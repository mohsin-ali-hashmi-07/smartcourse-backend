from fastapi import APIRouter
from app.api.routes.user_routes import router as user_router
from app.api.routes.auth_routes import router as auth_router

api_router = APIRouter()
api_router.include_router(user_router)
api_router.include_router(auth_router)