import os
from datetime import datetime, timezone
from typing import List, Optional

import grpc
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request


from log.config import configure_logging, get_logger 

from database.repository import get_repository   
from database.models import WeatherData          


from generated import weather_pb2 as m, weather_pb2_grpc as st 

configure_logging(service="weather-ui", level=os.getenv("LOG_LEVEL", "INFO"))
log = get_logger("ui")

UI_TITLE = os.getenv("UI_TITLE", "Weather Charts")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
GRPC_HOST = os.getenv("GRPC_HOST", os.getenv("GRPC_SERVER_HOST", "grpc-server"))
GRPC_PORT = int(os.getenv("GRPC_PORT", os.getenv("GRPC_SERVER_PORT", "50051")))
API_KEY  = os.getenv("SERVICE_API_KEY")

app = FastAPI(title=UI_TITLE)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ALLOW_ORIGINS == ["*"] else CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

def _to_dict(w: WeatherData) -> dict:
    d = w.model_dump()
    if isinstance(d.get("timestamp"), datetime):
        d["timestamp"] = d["timestamp"].isoformat()
    return d

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    repo = get_repository()
    cities = repo.get_all_cities()  
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": UI_TITLE,
            "cities": cities,
            "default_city": cities[0] if cities else "",
        },
    )

@app.get("/api/cities")
async def api_cities():
    repo = get_repository()
    cities = repo.get_all_cities()  
    return {"cities": cities}

@app.get("/api/history")
async def api_history(
    city: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=1000),
    start: Optional[str] = Query(None, description="ISO8601 start"),
    end: Optional[str]   = Query(None, description="ISO8601 end"),
):
    try:
        repo = get_repository()
        data: List[WeatherData] = repo.get_weather_history(city, limit=limit) 
        
        def parse_iso(s: Optional[str]) -> Optional[datetime]:
            if not s: return None
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                return None

        sdt, edt = parse_iso(start), parse_iso(end)
        if sdt or edt:
            def in_range(w: WeatherData) -> bool:
                ts = w.timestamp
                if isinstance(ts, datetime):
                    if ts.tzinfo is not None:
                        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
                if sdt and ts < sdt: return False
                if edt and ts > edt: return False
                return True
            
            data = [w for w in data if in_range(w)]
        
        return {"city": city.strip().title(), "count": len(data), "items": [_to_dict(w) for w in data]}
    
    except Exception as e:
        log.error("ui.history.error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch history")

@app.post("/api/refresh")
async def api_refresh(city: str = Query(..., min_length=1)):
    addr = f"{GRPC_HOST}:{GRPC_PORT}"
    metadata = [("x-api-key", API_KEY)] if API_KEY else None
    try:
        with grpc.insecure_channel(addr) as ch:
            stub = st.WeatherServiceStub(ch)
            resp = stub.GetWeather(m.WeatherRequest(city_name=city.strip()), metadata=metadata, timeout=10.0)
        return {
            "ok": True,
            "data": {
                "city_name": resp.city_name,
                "temperature": resp.temperature,
                "humidity": resp.humidity,
                "description": resp.description,
                "wind_speed": resp.wind_speed,
                "timestamp": resp.timestamp,
            },
        }
    except grpc.RpcError as e:
        return {"ok": False, "code": e.code().name, "details": e.details() or ""}
