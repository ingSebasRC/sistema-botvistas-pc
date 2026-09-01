"""Real-time log viewer widget."""

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from src.core.events import event_bridge


class LogViewer(QGroupBox):
    """Real-time terminal-like log console."""

    def __init__(self, parent: QWidget = None):
        super().__init__("📜 Registro de Actividad y Logs en Tiempo Real", parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        toolbar.addWidget(self.chk_autoscroll)

        toolbar.addStretch()

        self.btn_clear = QPushButton("Limpiar Consola")
        self.btn_clear.setObjectName("btn-secondary")
        self.btn_clear.clicked.connect(self._clear_logs)
        toolbar.addWidget(self.btn_clear)

        layout.addLayout(toolbar)

        # Log Text Box
        self.log_text = QPlainTextEdit()
        self.log_text.setObjectName("log-console")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        layout.addWidget(self.log_text)

    def _connect_signals(self) -> None:
        event_bridge.log_received.connect(self._on_log_received)
        event_bridge.device_log_received.connect(self._on_device_log_received)

    @Slot(str, str, str)
    def _on_log_received(self, level: str, timestamp: str, message: str) -> None:
        color_map = {
            "INFO": "#63B3ED",
            "WARNING": "#ECC94B",
            "ERROR": "#F56565",
            "CRITICAL": "#E53E3E",
            "DEBUG": "#718096"
        }
        color = color_map.get(level.upper(), "#CBD5E0")
        self._append_formatted(f"[{timestamp}] [{level}] {message}", color)

    @Slot(str, str)
    def _on_device_log_received(self, device_id: str, message: str) -> None:
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self._append_formatted(f"[{now}] [DEVICE {device_id}] {message}", "#B794F4")

    def _append_formatted(self, text: str, hex_color: str) -> None:
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        cursor.insertText(text + "\n", fmt)

        if self.chk_autoscroll.isChecked():
            self.log_text.ensureCursorVisible()

    def _clear_logs(self) -> None:
        self.log_text.clear()
