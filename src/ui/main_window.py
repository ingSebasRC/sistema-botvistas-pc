"""Main Application Window."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from src.core.config import settings
from src.core.logger import logger
from src.server.server_thread import server_thread
from src.ui.components.device_table import DeviceTable
from src.ui.components.log_viewer import LogViewer
from src.ui.components.server_status import ServerStatusWidget
from src.ui.components.task_panel import TaskPanel
from src.services.device_service import device_service
from adb_manager import AdbError


class MainWindow(QMainWindow):
    """Main desktop window for the BotVistas PC Control Panel."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{settings.app_name} v{settings.version}")
        self.resize(1100, 750)
        self.setMinimumSize(950, 600)
        self._setup_ui()
        self._usb_refresh_timer = QTimer(self)
        self._usb_refresh_timer.timeout.connect(self._refresh_usb_devices)
        self._usb_refresh_timer.start(3_000)
        self._refresh_usb_devices()

    def _refresh_usb_devices(self) -> None:
        """Refresh the table from ADB; USB discovery replaces WebSocket registration."""
        try:
            device_service.refresh_usb_devices()
        except AdbError as exc:
            logger.warning(f"No se pudo consultar ADB: {exc}")

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # 1. Header: Server status & IP info
        self.status_header = ServerStatusWidget()
        main_layout.addWidget(self.status_header)

        # 2. Main vertical splitter (Top: Devices & Tasks, Bottom: Logs)
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setChildrenCollapsible(False)

        # Top horizontal splitter (Left: Devices Table, Right: Task Config Panel)
        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setChildrenCollapsible(False)

        self.device_table = DeviceTable()
        self.task_panel = TaskPanel(get_selected_devices_cb=self.device_table.get_selected_device_ids)

        h_splitter.addWidget(self.device_table)
        h_splitter.addWidget(self.task_panel)
        h_splitter.setStretchFactor(0, 3)  # 60% width
        h_splitter.setStretchFactor(1, 2)  # 40% width

        v_splitter.addWidget(h_splitter)

        # 3. Bottom: Activity and Log Console
        self.log_viewer = LogViewer()
        v_splitter.addWidget(self.log_viewer)

        v_splitter.setStretchFactor(0, 3)
        v_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(v_splitter)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Gracefully terminate background services when window closes."""
        logger.info("Closing application. Shutting down server thread...")
        server_thread.stop()
        event.accept()
