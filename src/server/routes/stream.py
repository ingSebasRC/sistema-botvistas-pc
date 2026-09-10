"""USB live-video routes backed by scrcpy, not Android networking."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from adb_manager import AdbError, adb_manager
from stream_manager import StreamError, stream_manager

router = APIRouter(prefix="/api/stream", tags=["USB Stream"])


def _require_usb_device(serial: str) -> None:
    if not any(device.serial == serial and device.state == "device" for device in adb_manager.devices()):
        raise HTTPException(status_code=404, detail="Dispositivo USB ADB no disponible")


@router.get("/{serial}.mjpg")
def live_stream(serial: str):
    """Start/reuse headless scrcpy and serve its frames as MJPEG."""
    try:
        _require_usb_device(serial)
        return StreamingResponse(
            stream_manager.mjpeg_frames(serial),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store"},
        )
    except (AdbError, StreamError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{serial}", status_code=204)
def stop_stream(serial: str):
    stream_manager.stop(serial)
