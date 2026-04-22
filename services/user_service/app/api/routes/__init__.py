from fastapi import APIRouter
from app.api.routes.user_routes import router as user_router

api_router = APIRouter()
api_router.include_router(user_router)