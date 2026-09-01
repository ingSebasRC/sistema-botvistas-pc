"""Task execution REST API endpoints."""

from typing import Dict, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.models.task import Platform
from src.services.task_service import task_service

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


class StartTaskRequest(BaseModel):
    device_ids: List[str] = Field(..., min_length=1, description="List of target device IDs")
    platform: Platform = Field(default=Platform.YOUTUBE, description="Target platform (youtube or tiktok)")
    target_profile: str = Field(..., min_length=1, description="Target channel or profile")
    duration_per_video_seconds: int = Field(default=300, ge=10, description="Duration in seconds per video")


class StopTaskRequest(BaseModel):
    device_ids: List[str] = Field(..., min_length=1, description="List of target device IDs to stop")


@router.post("/start", response_model=Dict[str, bool])
async def start_task(req: StartTaskRequest):
    """Dispatch a task to one or multiple connected Android devices."""
    return await task_service.start_task(
        device_ids=req.device_ids,
        platform=req.platform,
        target_profile=req.target_profile,
        duration_per_video=req.duration_per_video_seconds
    )


@router.post("/stop", response_model=Dict[str, bool])
async def stop_task(req: StopTaskRequest):
    """Stop currently executing task on one or multiple devices."""
    return await task_service.stop_task(device_ids=req.device_ids)
