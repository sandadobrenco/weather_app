from datetime import datetime, timezone
from typing import TypedDict
from server.api_client import OpenWeatherClient, OpenWeatherError, CityNotFoundError
from log.config import get_logger

log = get_logger("weather_service")

class WeatherData(TypedDict):
    city_name: str
    temperature: float
    humidity: int
    description: str
    wind_speed: float
    timestamp: str

class WeatherService:
    def __init__(self, client: OpenWeatherClient = None):
        self.client = client or OpenWeatherClient()

    async def get_weather(self, city: str) -> WeatherData:
        try:
            log.info("service.get_weather", city=city)
            data = await self.client.fetch_weather(city)
            return {
                "city_name": data["name"],
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "wind_speed": data.get("wind", {}).get("speed", 0.0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except CityNotFoundError as e:
            log.warning("service.city_not_found", city=city)
            raise e
        except OpenWeatherError as e:
            log.error("service.owm_error", city=city, error=str(e))
            raise e
