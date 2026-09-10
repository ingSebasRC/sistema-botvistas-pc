"""Task configuration and execution control panel."""

from typing import Callable, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from src.core.logger import logger
from src.models.task import Platform
from src.server.app import run_async_coro
from src.services.task_service import task_service


class TaskPanel(QGroupBox):
    """Configuration panel to set up and dispatch automation tasks to selected devices."""

    def __init__(self, get_selected_devices_cb: Callable[[], List[str]], parent: QWidget = None):
        super().__init__("🎯 Configuración y Control de Tarea", parent)
        self._get_selected_devices = get_selected_devices_cb
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Platform selector
        self.combo_platform = QComboBox()
        self.combo_platform.addItem("🎥 YouTube", Platform.YOUTUBE)
        self.combo_platform.addItem("🎵 TikTok", Platform.TIKTOK)
        form_layout.addRow(QLabel("Plataforma Objetivo:"), self.combo_platform)

        # Target Profile / Channel
        self.input_profile = QLineEdit()
        self.input_profile.setPlaceholderText("Ej: @nombre_canal o URL del perfil")
        form_layout.addRow(QLabel("Canal / Perfil Objetivo:"), self.input_profile)

        # Duration per video
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(10, 7200)
        self.spin_duration.setValue(180)
        self.spin_duration.setSuffix(" segundos")
        form_layout.addRow(QLabel("Tiempo por Video:"), self.spin_duration)

        layout.addLayout(form_layout)

        # Help info
        info_lbl = QLabel("💡 Selecciona los dispositivos en la lista y presiona 'Iniciar Tarea'.")
        info_lbl.setStyleSheet("color: #718096; font-size: 11px;")
        layout.addWidget(info_lbl)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_start = QPushButton("▶ Iniciar Tarea")
        self.btn_start.setObjectName("btn-start")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Detener")
        self.btn_stop.setObjectName("btn-stop")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)

    def _on_start_clicked(self) -> None:
        target_profile = self.input_profile.text().strip()
        if not target_profile:
            QMessageBox.warning(self, "Campo Requerido", "Por favor ingresa un canal o perfil objetivo.")
            return

        selected_devices = self._get_selected_devices()
        if not selected_devices:
            logger.warning("Selecciona al menos un dispositivo de la lista.")
            QMessageBox.warning(self, "Dispositivos no seleccionados", "Selecciona al menos un dispositivo en la tabla.")
            return

        # QComboBox may return either the Platform enum or its string value,
        # depending on the Qt binding/serialization path.  Normalise it before
        # logging and dispatching so the click handler cannot fail on `.value`.
        platform = self.combo_platform.currentData()
        platform = getattr(platform, "value", platform)
        duration = self.spin_duration.value()

        logger.info(f"Enviando tarea ADB a {len(selected_devices)} dispositivo(s): {platform} -> {target_profile}")

        # Run coroutine on server event loop
        run_async_coro(task_service.start_task(
            device_ids=selected_devices,
            platform=platform,
            target_profile=target_profile,
            duration_per_video=duration
        ))

    def _on_stop_clicked(self) -> None:
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "Dispositivos no seleccionados", "Selecciona al menos un dispositivo en la tabla.")
            return

        logger.info(f"Stopping task on {len(selected_devices)} devices...")
        run_async_coro(task_service.stop_task(device_ids=selected_devices))
