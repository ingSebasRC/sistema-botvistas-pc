"""FastAPI Application factory and WebSocket endpoint definition."""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logger import logger
from src.server.routes.devices import router as devices_router
from src.server.routes.tasks import router as tasks_router
from src.server.ws_manager import ws_manager

# Active server event loop reference
_server_event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_server_event_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Retrieve the active asyncio event loop of the FastAPI server."""
    return _server_event_loop


def run_async_coro(coro):
    """Run an async coroutine on the server's event loop in a thread-safe manner."""
    loop = get_server_event_loop()
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        import threading
        t = threading.Thread(target=lambda: asyncio.run(coro), daemon=True)
        t.start()
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Server lifespan context manager."""
    global _server_event_loop
    _server_event_loop = asyncio.get_running_loop()
    logger.info(f"FastAPI Server running on {settings.host}:{settings.port} (LAN IP: {settings.local_ip})")
    yield
    _server_event_loop = None
    logger.info("FastAPI Server shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Local Server for Android Automation Multi-Device Management",
        lifespan=lifespan
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include REST routers
    app.include_router(devices_router)
    app.include_router(tasks_router)

    # Health Check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.version,
            "local_ip": settings.local_ip,
            "port": settings.port
        }

    # WebSocket Endpoint for Android devices
    @app.websocket("/ws/{device_id}")
    async def websocket_endpoint(websocket: WebSocket, device_id: str):
        await ws_manager.connect(device_id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await ws_manager.handle_incoming(device_id, data)
        except WebSocketDisconnect:
            ws_manager.disconnect(device_id)
        except Exception as e:
            logger.error(f"WebSocket error on device {device_id}: {e}")
            ws_manager.disconnect(device_id)

    return app


app = create_app()
