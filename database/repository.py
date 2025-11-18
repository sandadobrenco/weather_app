from typing import List, Optional
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from database.connection import get_collection
from database.models import WeatherData
from log.config import get_logger

logger = get_logger(__name__)

class WeatherRepository:
    def __init__(self, collection: Optional[Collection] = None):
        if collection is None:
            self.collection = get_collection('weather_data')
        else:
            self.collection = collection
        
        logger.info(
            "repository_initialized",
            collection=self.collection.name,
            database=self.collection.database.name
        )
    
    def save_weather(self, weather: WeatherData) -> str:
        try:
            logger.info(
                "weather_save_started",
                city=weather.city_name,
                temperature=weather.temperature
            )
            
            weather_dict = weather.model_dump()
            
            result = self.collection.insert_one(weather_dict)
            
            logger.info(
                "weather_saved",
                city=weather.city_name,
                document_id=str(result.inserted_id),
                temperature=weather.temperature,
                humidity=weather.humidity
            )
            
            return str(result.inserted_id)
        
        except PyMongoError as e:
            logger.error(
                "weather_save_failed",
                city=weather.city_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def get_latest_weather(self, city_name: str) -> Optional[WeatherData]:
        try:
            logger.debug("weather_fetch_latest", city=city_name)
            
            document = self.collection.find_one(
                {"city_name": city_name.strip().title()},
                sort=[("timestamp", -1)]
            )
            
            if document:
                document.pop('_id', None)
                
                logger.info(
                    "weather_latest_found",
                    city=city_name,
                    temperature=document.get('temperature'),
                    timestamp=document.get('timestamp')
                )
                
                return WeatherData(**document)
            
            logger.info("weather_latest_not_found", city=city_name)
            return None
        
        except PyMongoError as e:
            logger.error(
                "weather_fetch_failed",
                city=city_name,
                operation="get_latest",
                error=str(e)
            )
            raise
    
    def get_weather_history(self, city_name:str, limit: int= 100) -> List[WeatherData]:
        try:
            logger.debug(
                "weather_history_query",
                city=city_name,
                limit=limit
            )
            
            cursor = self.collection.find(
                {"city_name": city_name.strip().title()}
            ).sort("timestamp", -1).limit(limit)
            
            history = []
            for doc in cursor:
                doc.pop('_id', None)
                history.append(WeatherData(**doc))
            
            logger.info(
                "weather_history_retrieved",
                city=city_name,
                count=len(history),
                limit=limit
            )
            
            return history
        
        except PyMongoError as e:
            logger.error(
                "weather_history_failed",
                city=city_name,
                error=str(e)
            )
            raise
    
    def get_all_cities(self) -> List[str]:
        try:
            logger.debug("weather_cities_query")
            cities = self.collection.distinct("city_name")
            
            logger.info(
                "weather_cities_retrieved",
                count=len(cities),
                cities=sorted(cities)
            )
            
            return sorted(cities)
        
        except PyMongoError as e:
            logger.error("weather_cities_failed", error=str(e))
            raise
    
    def count_records(self, city_name: Optional[str] = None) -> int:
        try:
            query = {}
            if city_name:
                query["city_name"] = city_name.strip().title()
            
            count = self.collection.count_documents(query)
            
            logger.debug(
                "weather_count",
                city=city_name if city_name else "all",
                count=count
            )
            
            return count
            
        except PyMongoError as e:
            logger.error(
                "weather_count_failed",
                city=city_name if city_name else "all",
                error=str(e)
            )
            raise

def get_repository() -> WeatherRepository:
    return WeatherRepository()
                 