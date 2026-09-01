"""Task configuration and state models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported social media / video platforms."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class TaskStatus(str, Enum):
    """Execution status of an automation task."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class TaskConfig(BaseModel):
    """Automation task configuration assigned to a device."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique task ID")
    platform: Platform = Field(default=Platform.YOUTUBE, description="Target platform (youtube or tiktok)")
    target_profile: str = Field(..., min_length=1, description="Channel or profile name/URL to browse")
    duration_per_video_seconds: int = Field(default=300, ge=10, description="Playback duration per video in seconds")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current execution status")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = Field(default=None, description="Error details if failed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
