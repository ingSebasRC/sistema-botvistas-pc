"""Application configuration settings."""

import socket
from pydantic import BaseModel, Field


def get_local_ip() -> str:
    """Detect the local IP address on the Wi-Fi/LAN network."""
    try:
        # Connect to an external address (doesn't send packets) to find the outbound network interface
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class AppSettings(BaseModel):
    """Server and Application settings."""
    app_name: str = "BotVistas Server & Control Panel"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    local_ip: str = Field(default_factory=get_local_ip)
    heartbeat_timeout_seconds: int = 30
    log_level: str = "INFO"


# Global settings instance
settings = AppSettings()
