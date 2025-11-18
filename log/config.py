from __future__ import annotations
import sys, json, logging, logging.config, warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import structlog
from structlog import contextvars as ctxv
import orjson

def _json_dumps(o: Any, **kwargs) -> str:
    default = kwargs.pop("default", None)
    try:
        return orjson.dumps(o, option=orjson.OPT_OMIT_MICROSECONDS).decode()
    except Exception:
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"), default=default, **kwargs)

def _static_fields(service: str, runtime: str):
    def _proc(_logger, _method, event: dict):
        event.setdefault("service", service)
        event.setdefault("runtime", runtime)  # "dev" sau "prod"
        return event
    return _proc

def configure_logging(
    *, service: str = "weather-grpc", level: str = "INFO", dev: Optional[bool] = None
) -> None:
    if dev is None:
        dev = sys.stderr.isatty()
    runtime = "dev" if dev else "prod"

    # Warnings -> logging
    logging.captureWarnings(True)
    warnings.filterwarnings("default")

    # Handlers
    handlers = {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "structlog",
            "stream": "ext://sys.stdout",
        }
    }

    if dev:
        Path("logs").mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": level,
            "formatter": "structlog",
            "filename": "logs/application.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # Procesor care pasează recordurile prin pipeline-ul structlog
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": (
                    structlog.dev.ConsoleRenderer()
                    if dev
                    else structlog.processors.JSONRenderer(serializer=_json_dumps)
                ),
                "foreign_pre_chain": [
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    _static_fields(service, runtime),
                ],
            }
        },
        "handlers": handlers,
        "root": {"level": level, "handlers": list(handlers.keys())},
    })

    structlog.configure(
        processors=[
            ctxv.merge_contextvars,                   # context per request (async safe)
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _static_fields(service, runtime),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )

def get_logger(name: Optional[str] = None, **initial_ctx: Any) -> structlog.BoundLogger:
    log = structlog.get_logger(name) if name else structlog.get_logger()
    return log.bind(**initial_ctx) if initial_ctx else log

def bind_context(**kv: Any) -> None:
    if kv:
        ctxv.bind_contextvars(**kv)

def clear_context() -> None:
    ctxv.clear_contextvars()
