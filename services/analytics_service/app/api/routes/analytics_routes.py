from fastapi import APIRouter
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary():
    return analytics_service.get_summary()