"""Device data models and status definitions."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    """Possible connection and operational states of an Android device."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Device(BaseModel):
    """Represents a connected Android device."""
    device_id: str = Field(..., description="Unique hardware or UUID identifier of the Android device")
    name: str = Field(default="Android Device", description="Friendly display name")
    ip_address: str = Field(default="127.0.0.1", description="LAN IP address of the device")
    status: DeviceStatus = Field(default=DeviceStatus.CONNECTED, description="Current device status")
    battery_level: Optional[int] = Field(default=None, description="Battery percentage (0-100)")
    app_version: Optional[str] = Field(default=None, description="Installed APK version")
    current_task_id: Optional[str] = Field(default=None, description="Currently running task ID")
    current_platform: Optional[str] = Field(default=None, description="Active platform (youtube/tiktok)")
    last_seen: datetime = Field(default_factory=datetime.now, description="Timestamp of last message or heartbeat")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
