# Weather Microservice 

A simple **client–server** app built with **Python gRPC** that fetches live weather from **OpenWeatherMap**, persists snapshots to **MongoDB**, and exposes a small **FastAPI UI** to visualize historical temperature/humidity with charts.

> **Stack**: Python 3.12 · gRPC · FastAPI · httpx · MongoDB · Docker/Compose 

---

## ✨ Features

- **gRPC Server**
  - RPC: `GetWeather(city_name)`
  - Calls OpenWeatherMap **Current Weather API** and returns:
    - `city_name`, `temperature` (°C), `description`, `humidity` (%), `wind_speed`
  - protecteed gRPC endpoint with **x-api-key** 
  - Persists each successful response to MongoDB (`weather.weather_data`)

- **gRPC Client (CLI)**
  - Need to indicate the city name(ex. London)
  - Displays data in a user-friendly format, handles errors

- **Web UI (FastAPI)**
  - `/` – HTML page with 2 graphs (**temperature** & **humidity**) 

- **OpenWeatherMap Integration**
- 
- **MongoDB Persistence**

---

## ⚙️ Configuration

.env file example:

```
GRPC_KEY = my-key
GRPC_PORT=50051

OWM_API_KEY=put-your-owm-key-here
OWM_API_URL=https://api.openweathermap.org/data/2.5/weather

MONGODB_USERNAME=User
MONGODB_PASSWORD=User123
MONGODB_DB=weather
MONGODB_HOST=mongodb
MONGODB_PORT=27017

# Web UI
WEB_HOST=0.0.0.0
WEB_PORT=8000
UI_TITLE=Weather Charts
CORS_ALLOW_ORIGINS=*

SERVICE_API_KEY=my-key


HTTP_TIMEOUT=5
HTTP_RETRIES=2

---

## Running commands

docker compose up -d --build

gRPC client: Introduce a ciy name
docker compose exec grpc-client python -m client.weather_client --host grpc-server --port 50051


docker compose down

## 🗂 Repository Layout

