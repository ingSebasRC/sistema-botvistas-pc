"""Event bridge and Qt Signals for thread-safe cross-thread communication."""

from PySide6.QtCore import QObject, Signal


class EventBridge(QObject):
    """
    Thread-safe signal dispatcher bridging FastAPI/WebSockets and the PySide6 UI.
    Any event triggered by network calls emits signals handled in the main Qt thread.
    """

    # Device lifecycle signals
    device_registered = Signal(dict)         # dict: device info
    device_disconnected = Signal(str)        # str: device_id
    device_status_updated = Signal(dict)     # dict: device_id, status, details

    # Task signals
    task_status_updated = Signal(dict)       # dict: device_id, task_id, status, error_message

    # Log and telemetry signals
    log_received = Signal(str, str, str)     # str: level, str: timestamp, str: message
    device_log_received = Signal(str, str)   # str: device_id, str: log_message

    # Server state signals
    server_state_changed = Signal(bool, str, int)  # is_running, host_ip, port


# Singleton instance shared across the application
event_bridge = EventBridge()
