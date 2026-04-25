from fastapi import APIRouter
from app.api.routes.enrollment_routes import router as enrollment_router

api_router = APIRouter()
api_router.include_router(enrollment_router)