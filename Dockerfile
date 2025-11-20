FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ proto/
COPY generated/ ./generated/
COPY database/ ./database/
COPY log/ ./log/
COPY server/ ./server/
COPY client/ ./client/

# ============================================
# gRPC Server
# ============================================

FROM base as grpc-server

WORKDIR /app

EXPOSE 50051

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.close()" || exit 1

CMD ["python", "-m", "server.weather_server"]

# ============================================
# FastAPI UI 
# ============================================
FROM base as fastapi-app

WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1


CMD ["uvicorn", "client.ui.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# gRPC Client 
# ============================================
FROM base as grpc-client

WORKDIR /app


CMD ["python", "-m", "client.weather_client"]
