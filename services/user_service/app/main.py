from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.routes import api_router
from app.core.settings import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}