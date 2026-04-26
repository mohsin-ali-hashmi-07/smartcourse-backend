from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import api_router
from app.core.settings import settings
from app.kafka.consumer import start_consumer, stop_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_consumer()
    yield
    await stop_consumer()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}