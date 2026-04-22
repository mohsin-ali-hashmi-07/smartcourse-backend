from fastapi import APIRouter
from app.api.routes.course_routes import router as course_router

api_router = APIRouter()
api_router.include_router(course_router)