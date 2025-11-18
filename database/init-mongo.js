db = db.getSiblingDB('weather');

print('Initializing weather database');

db.createCollection('weather_data', {
    validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['city_name', 'temperature', 'timestamp'],
      properties: {
        city_name: {
          bsonType: 'string',
          description: 'City name - must be a string and is required'
        },
        temperature: {
          bsonType: 'double',
          description: 'Temperature in Celsius - must be a double and is required'
        },
        humidity: {
          bsonType: 'int',
          minimum: 0,
          maximum: 100,
          description: 'Humidity percentage - must be integer 0-100'
        },
        description: {
          bsonType: 'string',
          description: 'Weather description (e.g., clear sky, light rain)'
        },
        wind_speed: {
          bsonType: 'double',
          minimum: 0,
          description: 'Wind speed in m/s - must be positive'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Timestamp of weather data - required'
        }
      }
    }
  }
});

print('Collection "weather_data" created');

db.weather_data.createIndex(
  { 'city_name': 1, 'timestamp': -1 },
  { name: 'city_timestamp_idx' }
);

db.weather_data.createIndex(
  { 'timestamp': -1 },
  { name: 'timestamp_idx' }
);

print("Added indexes for city_name and timestamp")

print('Weather database initialization complete');