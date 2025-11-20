import os
import asyncio
import grpc

from generated import weather_pb2, weather_pb2_grpc
from server.config import cfg
from server.auth_interceptor import AuthInterceptor
from server.weather_service import WeatherService
from server.api_client import CityNotFoundError, OpenWeatherError  
from database.repository import get_repository
from database.models import WeatherData as WeatherDoc

from log.config import configure_logging, get_logger


configure_logging(service="weather-grpc", level=cfg.log_level, dev=os.getenv("ENV", "dev") == "dev")
log = get_logger("weather_server")

class WeatherServicer(weather_pb2_grpc.WeatherServiceServicer):
    def __init__(self):
        self.service = WeatherService()

    async def GetWeather(self, request, context):
        city = request.city_name.strip()
        if not city:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("City name cannot be empty")
            return weather_pb2.WeatherResponse()

        try:
            data = await self.service.get_weather(city)
            try:
                repo = get_repository()
                repo.save_weather(WeatherDoc(**data)) 
            except Exception as db_err:
                log.error("db.save_failed", error=str(db_err))
                
            return weather_pb2.WeatherResponse(
                city_name=data["city_name"],
                temperature=data["temperature"],
                humidity=data["humidity"],
                description=data["description"],
                wind_speed=data["wind_speed"],
                timestamp=data["timestamp"],
            )
        except CityNotFoundError as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return weather_pb2.WeatherResponse()
        except OpenWeatherError as e:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(str(e))
            return weather_pb2.WeatherResponse()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Unexpected error: {e}")
            return weather_pb2.WeatherResponse()

async def serve():
    server = grpc.aio.server(interceptors=[AuthInterceptor()])
    weather_pb2_grpc.add_WeatherServiceServicer_to_server(WeatherServicer(), server)
    address = f"{cfg.host}:{cfg.port}"
    server.add_insecure_port(address)
    log.info("Weather gRPC Server running", address=address)
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
