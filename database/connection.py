import os
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv
from log.config import get_logger 

load_dotenv()

logger = get_logger(__name__)

class MongoDBConnection:
    _instance: Optional["MongoDBConnection"] = None
    _client: Optional[MongoClient] = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            db_name = os.getenv('MONGODB_DB')
            host = os.getenv('MONGODB_HOST','mongodb')
            port = os.getenv('MONGODB_PORT','27017')
            
            self.mongo_uri = os.getenv('MONGO_URI', f'mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin')
            
            self.db_name = db_name
            
            logger.info(
                "mongo_config_loaded",
                database=self.db_name,
                host=host,
                port=port
            )
    
    def connect(self):
        if self._client is None:
            try:
                logger.info("mongodb_connecting", database=self.db_name)
                
                self._client = MongoClient(
                    self.mongo_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                )
                
                self._client.admin.command('ping')
                
                self._db = self._client[self.db_name]
                
                logger.info(
                    "mongodb_connected",
                    database=self.db_name,
                    collections=self._db.list_collection_names()
                )
                
            except ConnectionFailure as e:
                logger.error(
                    "mongodb_connection_failed",
                    database=self.db_name,
                    error=str(e),
                    error_type="ConnectionFailure"
                )
                raise
            except ServerSelectionTimeoutError as e:
                logger.error(
                    "mongodb_timeout",
                    database=self.db_name,
                    error=str(e),
                    error_type="ServerSelectionTimeout"
                )
                raise
            except Exception as e:
                logger.error(
                    "mongodb_unexpected_error",
                    database=self.db_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        return self._db
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("mongodb_connection_closed", database=self.db_name)
    
    @property
    def database(self):
        if self._db is None:
            self.connect()
        return self._db
    
    @property
    def client(self):
        if self._client is None:
            self.connect()
        return self._client
    
    def is_connected(self) -> bool:
        if self._client is None:
            return False
        
        try:
            self._client.admin.command('ping')
            return True
        except:
            logger.warning("mongodb_ping_failed", database=self.db_name)
            return False
    
    def get_collection(self, collection_name: str):
        logger.debug("mongodb_get_collection", collection=collection_name)
        return self.database[collection_name]
    
    def list_collections(self):
        collections = self.database.list_collection_names()
        logger.debug("mongodb_list_collections", count=len(collections), collections=collections)
        return collections
    
def get_database():

    conn = MongoDBConnection()
    return conn.database

def get_collection(collection_name: str = 'weather_data'):
    conn = MongoDBConnection()
    return conn.get_collection(collection_name)