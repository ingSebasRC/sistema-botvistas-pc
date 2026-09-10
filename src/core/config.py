"""Application configuration settings."""

from pydantic import BaseModel, Field


def get_local_ip() -> str:
    """Return the loopback host reserved for the local USB panel."""
    return "127.0.0.1"


class AppSettings(BaseModel):
    """Server and Application settings."""
    app_name: str = "BotVistas USB Control Panel"
    version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8000
    local_ip: str = Field(default_factory=get_local_ip)
    heartbeat_timeout_seconds: int = 30
    log_level: str = "INFO"


# Global settings instance
settings = AppSettings()
