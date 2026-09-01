"""Uvicorn server runner in a background thread."""

import threading
import uvicorn
from src.core.config import settings
from src.core.events import event_bridge
from src.core.logger import logger


class ServerThread(threading.Thread):
    """Manages the lifecycle of the Uvicorn server in a separate background thread."""

    def __init__(self, host: str = None, port: int = None):
        super().__init__(daemon=True, name="UvicornServerThread")
        self.host = host or settings.host
        self.port = port or settings.port
        self.config = uvicorn.Config(
            "src.server.app:app",
            host=self.host,
            port=self.port,
            log_level="warning",  # Keep uvicorn internals clean; app logger handles app logs
            access_log=False,
            loop="asyncio"
        )
        self.server = uvicorn.Server(self.config)
        self._is_running = False

    def run(self) -> None:
        """Run the Uvicorn server loop."""
        try:
            self._is_running = True
            logger.info(f"Starting server background thread on port {self.port}...")
            event_bridge.server_state_changed.emit(True, settings.local_ip, self.port)
            self.server.run()
        except Exception as e:
            logger.error(f"Server thread encountered an error: {e}", exc_info=True)
        finally:
            self._is_running = False
            event_bridge.server_state_changed.emit(False, settings.local_ip, self.port)
            logger.info("Server background thread stopped.")

    def stop(self) -> None:
        """Signal the server to stop and await termination."""
        if self._is_running:
            logger.info("Signaling Uvicorn server to stop...")
            self.server.should_exit = True
            self.join(timeout=3.0)


# Global server thread instance
server_thread = ServerThread()
