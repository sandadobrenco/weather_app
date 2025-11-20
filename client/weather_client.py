import os
import sys
import argparse
from datetime import datetime

import grpc
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

from generated import weather_pb2 as m, weather_pb2_grpc as st

try:
    from log.config import configure_logging, get_logger
    configure_logging(service="weather-client", level=os.getenv("LOG_LEVEL", "INFO"))
    log = get_logger("weather_client")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("weather_client")

TRANSIENT_CODES = {
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
    grpc.StatusCode.INTERNAL,
}

def _is_transient(e: BaseException) -> bool:
    return isinstance(e, grpc.RpcError) and e.code() in TRANSIENT_CODES

def _metadata(api_key: str | None):
    return [("x-api-key", api_key)] if api_key else None

def _fmt(resp: m.WeatherResponse) -> str:
    raw_ts = resp.timestamp
    ts_str = "-"
    if raw_ts:
        try:
            ts_str = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00")).isoformat()
        except Exception:
            ts_str = str(raw_ts)
    
    lines = [
        f"Weather for {resp.city_name}:",
        f"  Temperature: {resp.temperature} °C",
        f"  Humidity:    {resp.humidity}%",
        f"  Conditions:  {resp.description or '-'}",
        f"  Wind speed:  {resp.wind_speed} m/s",
        f"  Timestamp:   {ts_str}" if ts_str else "  Timestamp:   -",
    ]
    return "\n".join(lines)

@retry(
    reraise=True,
    stop=stop_after_attempt(int(os.getenv("CLIENT_RETRIES", "2"))),
    wait=wait_fixed(1),
    retry=retry_if_exception(_is_transient),
)
def get_weather(
    host: str,
    port: int,
    city: str,
    api_key: str | None,
    timeout: float,
) -> m.WeatherResponse:
    address = f"{host}:{port}"
    log.info("grpc.request", extra={"city": city, "address": address})
    with grpc.insecure_channel(address) as ch:
        stub = st.WeatherServiceStub(ch)
        try:
            resp: m.WeatherResponse = stub.GetWeather(
                m.WeatherRequest(city_name=city),
                metadata=_metadata(api_key),
                timeout=timeout,
            )
            log.info("grpc.response", extra={"city": resp.city_name, "ok": True})
            return resp
        except grpc.RpcError as e:
            code = e.code()
            details = e.details() or ""
            log.error(
                "grpc.error",
                extra={"code": str(code), "details": details, "city": city},
            )
            raise

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="weather-client",
        description="gRPC CLI client for WeatherService",
    )
    parser.add_argument("--host", default=os.getenv("GRPC_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("GRPC_PORT", "50051")))
    parser.add_argument("--api-key", default=os.getenv("SERVICE_API_KEY"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("CLIENT_TIMEOUT", "5")))
    parser.add_argument("--city", "-c", help="City name (e.g., London, Bucharest)")
    args = parser.parse_args(argv)

    city = args.city or input("Enter city name: ").strip()
    if not city:
        print("Please provide a non-empty city name.")
        return 2

    try:
        resp = get_weather(args.host, args.port, city, args.api_key, args.timeout)
        print(_fmt(resp))
        return 0
    except grpc.RpcError as e:
        code = e.code()
        msg = e.details() or str(code)
        message_code = {
            grpc.StatusCode.NOT_FOUND: "City not found. Check the name and try again.",
            grpc.StatusCode.UNAUTHENTICATED: "Missing or invalid x-api-key.",
            grpc.StatusCode.UNAVAILABLE: "Server unavailable. Please try again shortly.",
            grpc.StatusCode.INVALID_ARGUMENT: "Invalid input.",
            grpc.StatusCode.DEADLINE_EXCEEDED: "Request timed out.",
        }.get(code, f"gRPC error: {code.name}")

        print(f"{message_code}\nDetails: {msg}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
