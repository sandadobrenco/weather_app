import httpx
from httpx import RequestError, TimeoutException
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception
from server.config import cfg
from log.config import get_logger
from typing import Dict, Any

log = get_logger("api_client")

class OpenWeatherError(Exception): 
    pass
class CityNotFoundError(OpenWeatherError): 
    pass
class InvalidAPIKeyError(OpenWeatherError): 
    pass
class RateLimitError(OpenWeatherError): 
    pass

DETERMINISTIC_ERRORS = (InvalidAPIKeyError, CityNotFoundError)

class OpenWeatherClient:
    def __init__(self):
        self.base_url = cfg.owm_base_url
        self.api_key = cfg.owm_api_key
        self.timeout = cfg.http_timeout
    
    @retry(
        reraise=True,
        stop=stop_after_attempt(cfg.http_retries),
        wait=wait_fixed(1),
        retry=retry_if_exception(
            lambda e: isinstance(e, OpenWeatherError) and not isinstance(e, DETERMINISTIC_ERRORS)
        ),
    )

    async def fetch_weather(self, city: str) -> Dict[str, Any]:
        params = {"q": city, "appid": self.api_key, "units": "metric"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
        except TimeoutException as e:
            log.error("HTTP timeout", city=city, timeout=self.timeout)
            raise OpenWeatherError(f"Network timeout: {e}") from e
        except RequestError as e:
            log.error("HTTP network error", city=city, error=str(e))
            raise OpenWeatherError(f"Network error: {e}") from e

        log.info("HTTP response", city=city, status=response.status_code)

        if response.status_code == 401:
            raise InvalidAPIKeyError("Invalid OpenWeatherMap API key")
        elif response.status_code == 404:
            raise CityNotFoundError(f"City '{city}' not found")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code != 200:
            raise OpenWeatherError(f"Unexpected status code {response.status_code}")

        try:
            return response.json()
        except ValueError as e:
            log.error("Invalid JSON", city=city)
            raise OpenWeatherError("Incorrectly composed JSON from OpenWeather") from e
