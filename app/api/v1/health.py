from fastapi import APIRouter
from app.core.response import ApiResponse
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    return ApiResponse.ok(data={
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    })