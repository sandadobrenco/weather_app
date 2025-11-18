from datetime import datetime, timezone  
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal, ROUND_HALF_UP
class WeatherData(BaseModel):
    city_name: str = Field(...,
        min_length=1,
        max_length=100,
        description="Name of the city")
    
    temperature: float = Field(
        ...,
        ge=-100.0,
        le=100.0,
        description="Temperature in Celsius"
    )
    
    humidity: int = Field(
        ...,
        ge=0,
        le=100,
        description="Humidity percentage"
    )
    
    description: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Weather description"
    )
    
    wind_speed: Optional[float] = Field(
        None,
        ge=0.0,
        description="Wind speed in m/s (optional)",
        examples=[4.6, 3.2, 0.0]
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when data was recorded"
    )
    
    @field_validator('city_name')
    @classmethod
    def normalize_city_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('City name cannot be empty')
        return v.strip().title()
    
    @field_validator('description')
    @classmethod
    def normalize_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip().lower()

class OpenWeatherMain(BaseModel):
    temp: float
    humidity: int

class OpenWeatherDescription(BaseModel):
    description: str

class OpenWeatherWind(BaseModel):
    speed: float

class OpenWeatherResponse(BaseModel):
    name: str = Field(..., description="City name")
    main: OpenWeatherMain = Field(..., description="Temperature and humidity")
    weather: List[OpenWeatherDescription] = Field(..., description="Weather descriptions")
    wind: Optional[OpenWeatherWind] = Field(None, description="Wind data")
    
    
    def to_weather_data(self) -> WeatherData:
        temp_2 = float(Decimal(str(self.main.temp)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        wind_2 = (
        float(Decimal(str(self.wind.speed)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if self.wind else None)
    
        return WeatherData(
            city_name=self.name,
            temperature=temp_2,
            humidity=self.main.humidity,
            description=self.weather[0].description if self.weather else "unknown",
            wind_speed=wind_2,
            timestamp=datetime.now(timezone.utc)
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "London",
                "main": {
                    "temp": 18.55,
                    "humidity": 82
                },
                "weather": [
                    {
                        "description": "light rain"
                    }
                ],
                "wind": {
                    "speed": 4.6
                }
            }
        }
    )

__all__ = [
    "WeatherData",
    "OpenWeatherResponse",
]