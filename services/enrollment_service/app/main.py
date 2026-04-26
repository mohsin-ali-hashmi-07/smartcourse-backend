from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import api_router
from app.core.settings import settings
from app.core.kafka_producer import start_producer, stop_producer

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}