import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    host: str = os.getenv("GRPC_HOST", "0.0.0.0")
    port: int = int(os.getenv("GRPC_PORT", "50051"))

    service_api_key: str = os.getenv("SERVICE_API_KEY", "")

    owm_api_key: str = os.getenv("OWM_API_KEY", "")
    owm_base_url: str = os.getenv(
        "OWM_API_URL",
        "http://api.openweathermap.org/data/2.5/weather"
    )

    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "5"))
    http_retries: int = int(os.getenv("HTTP_RETRIES", "2"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

cfg = Config()
