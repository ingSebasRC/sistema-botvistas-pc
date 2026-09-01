"""WebSocket protocol message definitions between PC Server and Android Clients."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Types of messages exchanged via WebSocket."""
    # Android -> PC
    REGISTER = "REGISTER"
    HEARTBEAT = "HEARTBEAT"
    TASK_STATUS = "TASK_STATUS"
    LOG = "LOG"
    ERROR = "ERROR"

    # PC -> Android
    REGISTER_ACK = "REGISTER_ACK"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    TASK_START = "TASK_START"
    TASK_STOP = "TASK_STOP"
    CONFIG_UPDATE = "CONFIG_UPDATE"
    PING = "PING"


class WSClientMessage(BaseModel):
    """Standard message payload sent by an Android client to PC."""
    type: CommandType
    device_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)


class WSServerMessage(BaseModel):
    """Standard message payload sent by PC server to Android client(s)."""
    type: CommandType
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    task_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
