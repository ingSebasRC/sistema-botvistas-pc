"""Device registry and state management service."""

from datetime import datetime
from typing import Dict, List, Optional
from src.core.events import event_bridge
from src.core.logger import logger
from src.models.device import Device, DeviceStatus
from adb_manager import AdbDevice, adb_manager


class DeviceService:
    """Manages the lifecycle and state of all registered Android devices."""

    def __init__(self):
        self._devices: Dict[str, Device] = {}

    def register_device(
        self,
        device_id: str,
        name: str = "Android Device",
        ip_address: str = "127.0.0.1",
        battery_level: Optional[int] = None,
        app_version: Optional[str] = None
    ) -> Device:
        """Register or update an Android device."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.name = name or device.name
            device.ip_address = ip_address or device.ip_address
            device.status = DeviceStatus.CONNECTED
            device.battery_level = battery_level if battery_level is not None else device.battery_level
            device.app_version = app_version or device.app_version
            device.last_seen = datetime.now()
            logger.info(f"Device reconnected/updated: {device.name} ({device_id}) @ {ip_address}")
        else:
            device = Device(
                device_id=device_id,
                name=name,
                ip_address=ip_address,
                status=DeviceStatus.CONNECTED,
                battery_level=battery_level,
                app_version=app_version,
                last_seen=datetime.now()
            )
            self._devices[device_id] = device
            logger.info(f"New device registered: {device.name} ({device_id}) @ {ip_address}")

        event_bridge.device_registered.emit(device.model_dump())
        return device

    def mark_disconnected(self, device_id: str) -> None:
        """Mark a device as disconnected."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.status = DeviceStatus.DISCONNECTED
            device.last_seen = datetime.now()
            logger.warning(f"Device disconnected: {device.name} ({device_id})")
            event_bridge.device_disconnected.emit(device_id)

    def update_status(self, device_id: str, status: DeviceStatus, task_id: Optional[str] = None) -> None:
        """Update the operational status of a device."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.status = status
            device.last_seen = datetime.now()
            if task_id is not None:
                device.current_task_id = task_id
            logger.info(f"Device {device_id} status changed to {status.value}")
            event_bridge.device_status_updated.emit({
                "device_id": device_id,
                "status": status.value,
                "task_id": device.current_task_id,
                "battery": device.battery_level
            })

    def update_heartbeat(self, device_id: str, battery: Optional[int] = None) -> None:
        """Record a heartbeat signal from a device."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.last_seen = datetime.now()
            if battery is not None:
                device.battery_level = battery
            if device.status == DeviceStatus.DISCONNECTED:
                device.status = DeviceStatus.CONNECTED
                event_bridge.device_registered.emit(device.model_dump())

    def clear_current_task(self, device_id: str) -> None:
        """Clear a completed or cancelled task."""
        if device_id in self._devices:
            self._devices[device_id].current_task_id = None

    def get_device(self, device_id: str) -> Optional[Device]:
        """Retrieve a device by ID."""
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[Device]:
        """Get all registered devices."""
        return list(self._devices.values())

    def refresh_usb_devices(self) -> List[Device]:
        """Synchronize the registry with ``adb devices -l`` over USB."""
        detected = adb_manager.devices()
        active_serials = {item.serial for item in detected}
        for item in detected:
            if item.state == "device":
                self.register_device(
                    device_id=item.serial,
                    name=item.model,
                    ip_address="USB/ADB",
                    battery_level=item.battery_level,
                )
            else:
                # Keep unauthorized/offline phones visible, but never dispatch to them.
                self.register_device(device_id=item.serial, name=item.model, ip_address="USB/ADB")
                self.mark_disconnected(item.serial)
        for serial in set(self._devices) - active_serials:
            self.mark_disconnected(serial)
        return self.get_all_devices()


device_service = DeviceService()
