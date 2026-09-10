"""Device management REST API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.models.device import Device
from src.services.device_service import device_service
from adb_manager import AdbError

router = APIRouter(prefix="/api/devices", tags=["Devices"])


class DeviceRegisterRequest(BaseModel):
    device_id: str
    name: str = "Android Device"
    ip_address: Optional[str] = "127.0.0.1"
    battery_level: Optional[int] = None
    app_version: Optional[str] = None


@router.get("", response_model=List[Device])
async def list_devices():
    """Discover devices directly through the local USB ADB server."""
    try:
        return device_service.refresh_usb_devices()
    except AdbError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    """Retrieve a single device by ID."""
    dev = device_service.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return dev


@router.post("/register", response_model=Device)
async def register_device(req: DeviceRegisterRequest):
    """Register or update an Android device via HTTP."""
    dev = device_service.register_device(
        device_id=req.device_id,
        name=req.name,
        ip_address=req.ip_address or "127.0.0.1",
        battery_level=req.battery_level,
        app_version=req.app_version
    )
    return dev
