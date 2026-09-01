"""WebSocket connection manager for bidirectional communication with Android devices."""

import json
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

from src.core.events import event_bridge
from src.core.logger import logger
from src.models.device import DeviceStatus
from src.models.ws_messages import CommandType, WSServerMessage
from src.services.device_service import device_service


class ConnectionManager:
    """Manages active WebSocket connections to Android clients."""

    def __init__(self):
        self._active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """Accept and register a new device WebSocket connection."""
        await websocket.accept()
        self._active_connections[device_id] = websocket
        logger.info(f"WebSocket connected for device_id: {device_id}")

    def disconnect(self, device_id: str) -> None:
        """Unregister a disconnected device."""
        if device_id in self._active_connections:
            del self._active_connections[device_id]
            device_service.mark_disconnected(device_id)
            logger.info(f"WebSocket connection closed for device_id: {device_id}")

    def is_connected(self, device_id: str) -> bool:
        """Check if a device has an active WebSocket."""
        return device_id in self._active_connections

    async def send_to_device(self, device_id: str, message: WSServerMessage) -> bool:
        """Send a structured message to a specific device."""
        websocket = self._active_connections.get(device_id)
        if not websocket:
            logger.warning(f"Cannot send message: Device {device_id} is not connected via WebSocket")
            return False

        try:
            payload_str = message.model_dump_json()
            await websocket.send_text(payload_str)
            logger.debug(f"Sent {message.type.value} to {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to device {device_id}: {e}")
            self.disconnect(device_id)
            return False

    async def broadcast(self, message: WSServerMessage) -> None:
        """Broadcast a message to all connected devices."""
        for device_id in list(self._active_connections.keys()):
            await self.send_to_device(device_id, message)

    async def handle_incoming(self, device_id: str, raw_text: str) -> None:
        """Process incoming raw WebSocket message from Android device."""
        try:
            data = json.loads(raw_text)
            msg_type = data.get("type")
            payload = data.get("payload", {})

            logger.debug(f"Received from {device_id}: type={msg_type}")

            if msg_type == CommandType.REGISTER.value:
                name = payload.get("name", "Android Device")
                ip = payload.get("ip_address", "127.0.0.1")
                battery = payload.get("battery_level")
                version = payload.get("app_version")
                device_service.register_device(
                    device_id=device_id,
                    name=name,
                    ip_address=ip,
                    battery_level=battery,
                    app_version=version
                )
                # Reply ACK
                ack_msg = WSServerMessage(
                    type=CommandType.REGISTER_ACK,
                    payload={"status": "ok", "message": "Registered successfully"}
                )
                await self.send_to_device(device_id, ack_msg)

            elif msg_type == CommandType.HEARTBEAT.value:
                battery = payload.get("battery_level")
                device_service.update_heartbeat(device_id, battery=battery)
                ack_msg = WSServerMessage(
                    type=CommandType.HEARTBEAT_ACK,
                    payload={"status": "alive"}
                )
                await self.send_to_device(device_id, ack_msg)

            elif msg_type == CommandType.TASK_STATUS.value:
                status_str = payload.get("status", "idle")
                task_id = payload.get("task_id")
                err_msg = payload.get("error_message")

                try:
                    dev_status = DeviceStatus(status_str.lower())
                except ValueError:
                    dev_status = DeviceStatus.ERROR

                device_service.update_status(device_id, dev_status, task_id=task_id)
                event_bridge.task_status_updated.emit({
                    "device_id": device_id,
                    "task_id": task_id,
                    "status": status_str,
                    "error_message": err_msg
                })

            elif msg_type == CommandType.LOG.value:
                log_text = payload.get("message", "")
                event_bridge.device_log_received.emit(device_id, log_text)
                logger.info(f"[{device_id}] {log_text}")

            elif msg_type == CommandType.ERROR.value:
                err_text = payload.get("error", "Unknown client error")
                device_service.update_status(device_id, DeviceStatus.ERROR)
                event_bridge.device_log_received.emit(device_id, f"ERROR: {err_text}")
                logger.error(f"[{device_id}] Client reported error: {err_text}")

            else:
                logger.warning(f"Unknown message type '{msg_type}' from device {device_id}")

        except json.JSONDecodeError:
            logger.error(f"Malformed JSON from device {device_id}: {raw_text}")
        except Exception as e:
            logger.error(f"Error handling message from device {device_id}: {e}", exc_info=True)


ws_manager = ConnectionManager()
