"""Centralized logging configuration with Qt Signal integration."""

import logging
from datetime import datetime
from src.core.events import event_bridge


class QtLogHandler(logging.Handler):
    """Custom logging handler forwarding log records to PySide6 UI via EventBridge."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            message = self.format(record)
            event_bridge.log_received.emit(record.levelname, timestamp, message)
        except Exception:
            self.handleError(record)


def setup_logger(name: str = "botvistas", level: str = "INFO") -> logging.Logger:
    """Configure and return the main application logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        # Console handler with formatting
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Qt UI handler
        qt_handler = QtLogHandler()
        qt_formatter = logging.Formatter(fmt="%(message)s")
        qt_handler.setFormatter(qt_formatter)
        logger.addHandler(qt_handler)

    return logger


logger = setup_logger()
