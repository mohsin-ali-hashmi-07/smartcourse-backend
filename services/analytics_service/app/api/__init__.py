from fastapi import APIRouter
from app.api.routes.analytics_routes import router as analytics_router

api_router = APIRouter()
api_router.include_router(analytics_router)