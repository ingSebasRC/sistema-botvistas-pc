"""
server.py - Servidor FastAPI con WebSockets y rastreo de dispositivos en memoria.
"""

import asyncio
import json
import logging
import socket
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("server")


def get_local_ip() -> str:
    """Detecta la dirección IP local en la red Wi-Fi/LAN."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class DeviceInfo(BaseModel):
    """Modelo de datos para un dispositivo Android en memoria."""
    device_id: str
    name: str = "Android Device"
    ip_address: str = "127.0.0.1"
    status: str = "connected"  # connected, idle, running, stopped, error, disconnected
    battery_level: Optional[int] = None
    app_version: Optional[str] = None
    last_seen: str = ""
    current_task: Optional[Dict[str, Any]] = None


class DeviceManager:
    """Mecanismo en memoria para rastrear dispositivos conectados y gestionar WebSockets."""

    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.active_websockets: Dict[str, WebSocket] = {}
        # Callbacks opcionales para notificar a la UI u otros módulos
        self.on_device_connected: Optional[Callable[[DeviceInfo], None]] = None
        self.on_device_disconnected: Optional[Callable[[str], None]] = None
        self.on_device_status_changed: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
        self.on_log_received: Optional[Callable[[str, str], None]] = None

    async def register_connection(self, device_id: str, websocket: WebSocket, client_ip: str) -> DeviceInfo:
        """Registra la conexión WebSocket entrante de un dispositivo."""
        now_str = datetime.now().strftime("%H:%M:%S")
        if device_id in self.devices:
            dev = self.devices[device_id]
            dev.ip_address = client_ip
            dev.status = "connected"
            dev.last_seen = now_str
        else:
            dev = DeviceInfo(
                device_id=device_id,
                name=f"Android ({device_id[:6]})",
                ip_address=client_ip,
                status="connected",
                last_seen=now_str
            )
            self.devices[device_id] = dev

        self.active_websockets[device_id] = websocket
        logger.info(f"Dispositivo conectado: {device_id} desde {client_ip}")

        if self.on_device_connected:
            self.on_device_connected(dev)

        return dev

    def unregister_connection(self, device_id: str) -> None:
        """Desconecta y actualiza el estado en memoria."""
        if device_id in self.active_websockets:
            del self.active_websockets[device_id]

        if device_id in self.devices:
            dev = self.devices[device_id]
            dev.status = "disconnected"
            dev.last_seen = datetime.now().strftime("%H:%M:%S")
            logger.warning(f"Dispositivo desconectado: {device_id}")

            if self.on_device_disconnected:
                self.on_device_disconnected(device_id)

    async def send_to_device(self, device_id: str, message: dict) -> bool:
        """Envía un comando o mensaje JSON a un dispositivo específico."""
        ws = self.active_websockets.get(device_id)
        if not ws:
            logger.warning(f"No se pudo enviar mensaje: dispositivo {device_id} no está conectado.")
            return False

        try:
            await ws.send_text(json.dumps(message))
            logger.info(f"Mensaje enviado a {device_id}: {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar mensaje a {device_id}: {e}")
            self.unregister_connection(device_id)
            return False

    async def broadcast(self, message: dict) -> None:
        """Envía un mensaje JSON a todos los dispositivos conectados."""
        for device_id in list(self.active_websockets.keys()):
            await self.send_to_device(device_id, message)

    def update_status(self, device_id: str, status: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Actualiza el estado operativo de un dispositivo."""
        if device_id in self.devices:
            dev = self.devices[device_id]
            dev.status = status
            dev.last_seen = datetime.now().strftime("%H:%M:%S")
            if self.on_device_status_changed:
                self.on_device_status_changed(device_id, status, payload or {})

    def get_all_devices(self) -> List[DeviceInfo]:
        """Obtiene la lista de todos los dispositivos en memoria."""
        return list(self.devices.values())


# Instancia global del gestor de dispositivos
device_manager = DeviceManager()

# Instancia global del bucle de eventos del servidor
server_event_loop: Optional[asyncio.AbstractEventLoop] = None


def create_app() -> FastAPI:
    """Fábrica de la aplicación FastAPI."""
    app = FastAPI(
        title="BotVistas Multi-Device Server",
        description="Servidor de comunicación y orquestación para dispositivos Android",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        global server_event_loop
        server_event_loop = asyncio.get_running_loop()
        logger.info(f"Servidor FastAPI iniciado en http://{get_local_ip()}:8000")

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "server_ip": get_local_ip(),
            "port": 8000,
            "connected_devices": len(device_manager.active_websockets)
        }

    @app.get("/devices")
    async def get_devices():
        return device_manager.get_all_devices()

    # Endpoint WebSocket principal
    @app.websocket("/ws/{device_id}")
    async def websocket_endpoint(websocket: WebSocket, device_id: str):
        await websocket.accept()
        client_ip = websocket.client.host if websocket.client else "127.0.0.1"
        await device_manager.register_connection(device_id, websocket, client_ip)

        try:
            while True:
                data_text = await websocket.receive_text()
                try:
                    data = json.loads(data_text)
                    msg_type = data.get("type", "").upper()
                    payload = data.get("payload", {})

                    if msg_type == "REGISTER":
                        if device_id in device_manager.devices:
                            dev = device_manager.devices[device_id]
                            dev.name = payload.get("name", dev.name)
                            dev.battery_level = payload.get("battery_level", dev.battery_level)
                            dev.app_version = payload.get("app_version", dev.app_version)
                            if device_manager.on_device_connected:
                                device_manager.on_device_connected(dev)

                        # Enviar ACK de registro
                        await device_manager.send_to_device(device_id, {
                            "type": "REGISTER_ACK",
                            "payload": {"status": "ok"}
                        })

                    elif msg_type == "HEARTBEAT":
                        if device_id in device_manager.devices:
                            dev = device_manager.devices[device_id]
                            dev.battery_level = payload.get("battery_level", dev.battery_level)
                            dev.last_seen = datetime.now().strftime("%H:%M:%S")
                            if device_manager.on_device_status_changed:
                                device_manager.on_device_status_changed(device_id, dev.status, payload)

                        # Responder Heartbeat
                        await device_manager.send_to_device(device_id, {
                            "type": "HEARTBEAT_ACK",
                            "payload": {"status": "alive"}
                        })

                    elif msg_type == "TASK_STATUS":
                        status = payload.get("status", "idle")
                        device_manager.update_status(device_id, status, payload)

                    elif msg_type == "LOG":
                        log_msg = payload.get("message", "")
                        if device_manager.on_log_received:
                            device_manager.on_log_received(device_id, log_msg)
                        logger.info(f"[{device_id}] {log_msg}")

                except json.JSONDecodeError:
                    logger.error(f"Mensaje no válido de {device_id}: {data_text}")

        except WebSocketDisconnect:
            device_manager.unregister_connection(device_id)
        except Exception as e:
            logger.error(f"Excepción en WebSocket de {device_id}: {e}")
            device_manager.unregister_connection(device_id)

    return app


app = create_app()


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Ejecuta el servidor Uvicorn en modo síncrono (bloqueante)."""
    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    run_server()
