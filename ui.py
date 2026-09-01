"""
ui.py - Interfaz gráfica en PySide6 con integración del hilo de servidor FastAPI.
"""

import asyncio
import sys
import threading
from datetime import datetime
from typing import Dict, List

import uvicorn
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from server import DeviceInfo, app, device_manager, get_local_ip

# Estilos QSS para tema oscuro moderno
MODERN_DARK_THEME = """
QWidget {
    background-color: #121418;
    color: #E2E8F0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 8px;
    margin-top: 22px;
    padding-top: 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    color: #63B3ED;
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 4px;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #242933;
    border: 1px solid #3E4C5E;
    border-radius: 6px;
    padding: 8px 12px;
    color: #F7FAFC;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4299E1;
    background-color: #2A303C;
}

QPushButton {
    background-color: #2B6CB0;
    color: #FFFFFF;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
}

QPushButton:hover {
    background-color: #3182CE;
}

QPushButton#btn-start {
    background-color: #2E7D32;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: bold;
    padding: 10px;
}
QPushButton#btn-start:hover {
    background-color: #388E3C;
}

QPushButton#btn-stop {
    background-color: #C62828;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: bold;
    padding: 10px;
}
QPushButton#btn-stop:hover {
    background-color: #D32F2F;
}

QPushButton#btn-secondary {
    background-color: #2D3748;
    color: #E2E8F0;
    border: 1px solid #4A5568;
}
QPushButton#btn-secondary:hover {
    background-color: #3E4C5E;
}

QTableWidget {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 8px;
    gridline-color: #2D3748;
}

QHeaderView::section {
    background-color: #242933;
    color: #A0AEC0;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2D3748;
}

QPlainTextEdit#log-console {
    background-color: #0B0D11;
    color: #A0AEC0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 8px;
}
"""


class BridgeSignals(QObject):
    """Puente de señales para comunicar eventos del servidor FastAPI con la interfaz gráfica."""
    device_connected = Signal(dict)
    device_disconnected = Signal(str)
    device_status_changed = Signal(str, str, dict)
    log_received = Signal(str, str)
    server_status = Signal(bool, str, int)


# Instancia del puente de señales
bridge = BridgeSignals()


class ServerThread(threading.Thread):
    """Hilo secundario que corre el servidor FastAPI / Uvicorn."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(daemon=True, name="FastAPIServerThread")
        self.host = host
        self.port = port
        self.server: Optional[uvicorn.Server] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_running = False

    def run(self):
        self._is_running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        bridge.server_status.emit(True, get_local_ip(), self.port)

        try:
            self.server.run()
        except Exception as e:
            bridge.log_received.emit("SERVER", f"Error en servidor: {e}")
        finally:
            self._is_running = False
            bridge.server_status.emit(False, get_local_ip(), self.port)

    def stop(self):
        if self.server and self._is_running:
            self.server.should_exit = True
            self.join(timeout=2.0)

    def dispatch_coroutine(self, coro):
        """Ejecuta una corrutina en el bucle del servidor de forma segura."""
        if self.loop and self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            threading.Thread(target=lambda: asyncio.run(coro), daemon=True).start()
            return None


class MainWindow(QMainWindow):
    """Ventana principal del Panel de Control BotVistas."""

    def __init__(self, server_thread: ServerThread):
        super().__init__()
        self.server_thread = server_thread
        self.setWindowTitle("BotVistas - Servidor PC y Panel de Control")
        self.resize(1050, 720)
        self.setMinimumSize(900, 600)
        self._row_map: Dict[str, int] = {}

        self._setup_ui()
        self._setup_server_callbacks()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # 1. Header de Estado del Servidor
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1A1D24; border: 1px solid #2D3748; border-radius: 8px; padding: 8px;")
        header_layout = QHBoxLayout(header_frame)

        app_title = QLabel("🤖 BotVistas Control Hub")
        app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        header_layout.addWidget(app_title)

        header_layout.addStretch()

        self.lbl_server_status = QLabel("🟢 Servidor Activo")
        self.lbl_server_status.setStyleSheet("background-color: #1C3829; color: #48BB78; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
        header_layout.addWidget(self.lbl_server_status)

        self.lbl_server_ip = QLabel(f"IP: {get_local_ip()}:8000")
        self.lbl_server_ip.setStyleSheet("font-weight: bold; color: #63B3ED; font-size: 13px;")
        header_layout.addWidget(self.lbl_server_ip)

        btn_copy = QPushButton("📋 Copiar IP")
        btn_copy.setObjectName("btn-secondary")
        btn_copy.clicked.connect(self._copy_ip)
        header_layout.addWidget(btn_copy)

        self.lbl_device_count = QLabel("0 Conectados")
        self.lbl_device_count.setStyleSheet("color: #F6AD55; font-weight: bold;")
        header_layout.addWidget(self.lbl_device_count)

        main_layout.addWidget(header_frame)

        # 2. Splitter Vertical (Panel Central + Consola de Logs)
        v_splitter = QSplitter(Qt.Vertical)

        # Splitter Horizontal (Tabla Dispositivos + Panel de Tarea)
        h_splitter = QSplitter(Qt.Horizontal)

        # A. Tabla de Dispositivos
        devices_group = QGroupBox("📱 Dispositivos Conectados")
        dev_layout = QVBoxLayout(devices_group)

        dev_toolbar = QHBoxLayout()
        btn_sel_all = QPushButton("Seleccionar Todos")
        btn_sel_all.setObjectName("btn-secondary")
        btn_sel_all.clicked.connect(self._select_all_devices)
        btn_desel = QPushButton("Deseleccionar")
        btn_desel.setObjectName("btn-secondary")
        btn_desel.clicked.connect(self._deselect_all_devices)
        dev_toolbar.addWidget(btn_sel_all)
        dev_toolbar.addWidget(btn_desel)
        dev_toolbar.addStretch()
        dev_layout.addLayout(dev_toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Sel", "Nombre", "ID Dispositivo", "IP", "Estado", "Batería"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        dev_layout.addWidget(self.table)

        h_splitter.addWidget(devices_group)

        # B. Panel de Configuración de Tareas
        task_group = QGroupBox("🎯 Asignar y Controlar Tarea")
        task_layout = QVBoxLayout(task_group)
        task_form = QFormLayout()
        task_form.setSpacing(12)

        self.combo_platform = QComboBox()
        self.combo_platform.addItems(["🎥 YouTube", "🎵 TikTok"])
        task_form.addRow(QLabel("Plataforma:"), self.combo_platform)

        self.input_target = QLineEdit()
        self.input_target.setPlaceholderText("Ej: @canal_objetivo o perfil")
        task_form.addRow(QLabel("Canal / Perfil:"), self.input_target)

        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(10, 7200)
        self.spin_duration.setValue(180)
        self.spin_duration.setSuffix(" seg")
        task_form.addRow(QLabel("Tiempo por Video:"), self.spin_duration)

        task_layout.addLayout(task_form)
        task_layout.addStretch()

        task_btns = QHBoxLayout()
        self.btn_start = QPushButton("▶ Iniciar Tarea")
        self.btn_start.setObjectName("btn-start")
        self.btn_start.clicked.connect(self._start_task)
        self.btn_stop = QPushButton("⏹ Detener")
        self.btn_stop.setObjectName("btn-stop")
        self.btn_stop.clicked.connect(self._stop_task)
        task_btns.addWidget(self.btn_start)
        task_btns.addWidget(self.btn_stop)
        task_layout.addLayout(task_btns)

        h_splitter.addWidget(task_group)
        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 2)

        v_splitter.addWidget(h_splitter)

        # C. Consola de Logs
        log_group = QGroupBox("📜 Registro en Tiempo Real")
        log_layout = QVBoxLayout(log_group)
        self.log_console = QPlainTextEdit()
        self.log_console.setObjectName("log-console")
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_console)

        v_splitter.addWidget(log_group)
        v_splitter.setStretchFactor(0, 3)
        v_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(v_splitter)

    def _setup_server_callbacks(self):
        """Conecta los callbacks de device_manager hacia las señales de Qt."""
        device_manager.on_device_connected = lambda dev: bridge.device_connected.emit(dev.model_dump())
        device_manager.on_device_disconnected = lambda dev_id: bridge.device_disconnected.emit(dev_id)
        device_manager.on_device_status_changed = lambda dev_id, status, payload: bridge.device_status_changed.emit(dev_id, status, payload)
        device_manager.on_log_received = lambda dev_id, msg: bridge.log_received.emit(dev_id, msg)

    def _connect_signals(self):
        """Conecta las señales de Qt a los slots de la interfaz."""
        bridge.device_connected.connect(self._on_device_connected)
        bridge.device_disconnected.connect(self._on_device_disconnected)
        bridge.device_status_changed.connect(self._on_device_status_changed)
        bridge.log_received.connect(self._on_log_received)
        bridge.server_status.connect(self._on_server_status)

    def _copy_ip(self):
        QApplication.clipboard().setText(f"{get_local_ip()}:8000")
        self._append_log("SISTEMA", f"Dirección {get_local_ip()}:8000 copiada al portapapeles.")

    def _select_all_devices(self):
        for r in range(self.table.rowCount()):
            cell = self.table.cellWidget(r, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk:
                    chk.setChecked(True)

    def _deselect_all_devices(self):
        for r in range(self.table.rowCount()):
            cell = self.table.cellWidget(r, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk:
                    chk.setChecked(False)

    def _get_selected_device_ids(self) -> List[str]:
        selected = []
        for r in range(self.table.rowCount()):
            cell = self.table.cellWidget(r, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk and chk.isChecked():
                    id_item = self.table.item(r, 2)
                    if id_item:
                        selected.append(id_item.text())
        return selected

    def _update_device_count(self):
        active = sum(1 for d in device_manager.get_all_devices() if d.status != "disconnected")
        self.lbl_device_count.setText(f"{active} Conectados")

    @Slot(dict)
    def _on_device_connected(self, data: dict):
        device_id = data.get("device_id")
        if not device_id:
            return

        if device_id in self._row_map:
            row = self._row_map[device_id]
        else:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._row_map[device_id] = row

            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            layout = QHBoxLayout(chk_widget)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, chk_widget)

        self.table.setItem(row, 1, QTableWidgetItem(data.get("name", "Android")))
        self.table.setItem(row, 2, QTableWidgetItem(device_id))
        self.table.setItem(row, 3, QTableWidgetItem(data.get("ip_address", "127.0.0.1")))

        status_lbl = QLabel("🟢 Conectado")
        status_lbl.setStyleSheet("color: #48BB78; font-weight: bold;")
        status_lbl.setAlignment(Qt.AlignCenter)
        self.table.setCellWidget(row, 4, status_lbl)

        bat = data.get("battery_level")
        bat_item = QTableWidgetItem(f"{bat}%" if bat is not None else "--")
        bat_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 5, bat_item)

        self._update_device_count()
        self._append_log("CONEXIÓN", f"Dispositivo registrado: {data.get('name')} ({device_id})")

    @Slot(str)
    def _on_device_disconnected(self, device_id: str):
        if device_id in self._row_map:
            row = self._row_map[device_id]
            lbl = QLabel("⚪ Desconectado")
            lbl.setStyleSheet("color: #718096;")
            lbl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, lbl)
        self._update_device_count()
        self._append_log("CONEXIÓN", f"Dispositivo desconectado: {device_id}")

    @Slot(str, str, dict)
    def _on_device_status_changed(self, device_id: str, status: str, payload: dict):
        if device_id in self._row_map:
            row = self._row_map[device_id]
            color_map = {
                "running": ("⚡ Ejecutando", "#63B3ED"),
                "stopped": ("⏹ Detenido", "#ECC94B"),
                "error": ("❌ Error", "#F56565"),
                "connected": ("🟢 Disponible", "#48BB78"),
            }
            text, color = color_map.get(status.lower(), (status, "#CBD5E0"))
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            lbl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, lbl)

            bat = payload.get("battery_level")
            if bat is not None:
                bat_item = QTableWidgetItem(f"{bat}%")
                bat_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, bat_item)

    @Slot(str, str)
    def _on_log_received(self, origin: str, message: str):
        self._append_log(origin, message)

    @Slot(bool, str, int)
    def _on_server_status(self, is_running: bool, host: str, port: int):
        if is_running:
            self.lbl_server_status.setText("🟢 Servidor Activo")
            self.lbl_server_status.setStyleSheet("background-color: #1C3829; color: #48BB78; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
            self._append_log("SERVIDOR", f"Servidor iniciado en http://{host}:{port}")
        else:
            self.lbl_server_status.setText("🔴 Servidor Detenido")
            self.lbl_server_status.setStyleSheet("background-color: #441A1A; color: #F56565; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
            self._append_log("SERVIDOR", "Servidor detenido.")

    def _append_log(self, tag: str, text: str):
        time_str = datetime.now().strftime("%H:%M:%S")
        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#63B3ED" if tag == "SERVIDOR" else "#B794F4" if tag == "CONEXIÓN" else "#E2E8F0"))
        cursor.insertText(f"[{time_str}] [{tag}] {text}\n", fmt)
        self.log_console.ensureCursorVisible()

    def _start_task(self):
        target = self.input_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Atención", "Ingresa un canal o perfil objetivo.")
            return

        devices = self._get_selected_device_ids()
        if not devices:
            QMessageBox.warning(self, "Atención", "Selecciona al menos un dispositivo en la tabla.")
            return

        platform_name = "youtube" if "YouTube" in self.combo_platform.currentText() else "tiktok"
        duration = self.spin_duration.value()

        task_msg = {
            "type": "TASK_START",
            "payload": {
                "platform": platform_name,
                "target_profile": target,
                "duration_per_video_seconds": duration
            }
        }

        for dev_id in devices:
            self.server_thread.dispatch_coroutine(device_manager.send_to_device(dev_id, task_msg))
            device_manager.update_status(dev_id, "running")

        self._append_log("TAREA", f"Iniciada tarea en {len(devices)} dispositivos: {platform_name} -> {target}")

    def _stop_task(self):
        devices = self._get_selected_device_ids()
        if not devices:
            QMessageBox.warning(self, "Atención", "Selecciona al menos un dispositivo.")
            return

        stop_msg = {
            "type": "TASK_STOP",
            "payload": {"reason": "Detenido manualmente desde PC"}
        }

        for dev_id in devices:
            self.server_thread.dispatch_coroutine(device_manager.send_to_device(dev_id, stop_msg))
            device_manager.update_status(dev_id, "stopped")

        self._append_log("TAREA", f"Detenida tarea en {len(devices)} dispositivos.")

    def closeEvent(self, event):
        """Detiene el servidor al cerrar la ventana."""
        self._append_log("SISTEMA", "Cerrando aplicación...")
        self.server_thread.stop()
        event.accept()


def create_gui_app():
    """Inicializa y arranca la aplicación gráfica PySide6 junto con el servidor."""
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(MODERN_DARK_THEME)

    # Iniciar servidor en hilo secundario
    server_thread = ServerThread(host="0.0.0.0", port=8000)
    server_thread.start()

    # Iniciar ventana principal
    window = MainWindow(server_thread)
    window.show()

    exit_code = qt_app.exec()
    server_thread.stop()
    sys.exit(exit_code)
