"""Server status header widget."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from src.core.config import settings
from src.core.events import event_bridge


class ServerStatusWidget(QFrame):
    """Header widget displaying server IP, port, status, and connection count."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("server-status-card")
        self.setStyleSheet("""
            QFrame#server-status-card {
                background-color: #1A1D24;
                border: 1px solid #2D3748;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self._connected_count = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(20)

        # Title & App info
        left_layout = QVBoxLayout()
        title_label = QLabel("🚀 BotVistas Automation Hub")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        subtitle_label = QLabel("Panel de Control y Servidor Local Multi-Dispositivo")
        subtitle_label.setStyleSheet("color: #718096; font-size: 12px;")
        left_layout.addWidget(title_label)
        left_layout.addWidget(subtitle_label)
        layout.addLayout(left_layout)

        layout.addStretch()

        # Status Badge
        self.status_badge = QLabel("🟢 En Línea")
        self.status_badge.setStyleSheet("""
            background-color: #1C3829;
            color: #48BB78;
            font-weight: bold;
            border-radius: 6px;
            padding: 6px 12px;
            border: 1px solid #276749;
        """)
        layout.addWidget(self.status_badge)

        # Local FastAPI endpoint for USB video frames
        server_info_layout = QVBoxLayout()
        ip_label = QLabel("Servidor local USB:")
        ip_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        self.ip_value = QLabel(f"{settings.local_ip}:{settings.port}")
        self.ip_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #63B3ED;")
        server_info_layout.addWidget(ip_label)
        server_info_layout.addWidget(self.ip_value)
        layout.addLayout(server_info_layout)

        # Copy IP Button
        self.btn_copy_ip = QPushButton("📋 Copiar IP")
        self.btn_copy_ip.setObjectName("btn-secondary")
        self.btn_copy_ip.setCursor(Qt.PointingHandCursor)
        self.btn_copy_ip.clicked.connect(self._copy_ip_to_clipboard)
        layout.addWidget(self.btn_copy_ip)

        # Active Devices Count
        count_layout = QVBoxLayout()
        count_title = QLabel("Dispositivos:")
        count_title.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        self.count_value = QLabel("0 Conectados")
        self.count_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #F6AD55;")
        count_layout.addWidget(count_title)
        count_layout.addWidget(self.count_value)
        layout.addLayout(count_layout)

    def _connect_signals(self) -> None:
        event_bridge.server_state_changed.connect(self._on_server_state_changed)
        event_bridge.device_registered.connect(self._on_device_updated)
        event_bridge.device_disconnected.connect(self._on_device_disconnected)

    def _copy_ip_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{settings.local_ip}:{settings.port}")
        self.btn_copy_ip.setText("✔ Copiado")
        # Reset text after a second
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_copy_ip.setText("📋 Copiar IP"))

    @Slot(bool, str, int)
    def _on_server_state_changed(self, is_running: bool, host: str, port: int) -> None:
        if is_running:
            self.status_badge.setText("🟢 En Línea")
            self.status_badge.setStyleSheet("""
                background-color: #1C3829;
                color: #48BB78;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
                border: 1px solid #276749;
            """)
            self.ip_value.setText(f"{host}:{port}")
        else:
            self.status_badge.setText("🔴 Detenido")
            self.status_badge.setStyleSheet("""
                background-color: #441A1A;
                color: #F56565;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
                border: 1px solid #742A2A;
            """)

    @Slot(dict)
    def _on_device_updated(self, device_data: dict) -> None:
        from src.services.device_service import device_service
        devices = device_service.get_all_devices()
        connected = sum(1 for d in devices if d.status.value != "disconnected")
        self.count_value.setText(f"{connected} Conectados")

    @Slot(str)
    def _on_device_disconnected(self, device_id: str) -> None:
        from src.services.device_service import device_service
        devices = device_service.get_all_devices()
        connected = sum(1 for d in devices if d.status.value != "disconnected")
        self.count_value.setText(f"{connected} Conectados")
