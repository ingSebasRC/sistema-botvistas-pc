"""Device table widget for managing connected Android clients."""

from datetime import datetime
from typing import Dict, List
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.core.events import event_bridge
from src.models.device import DeviceStatus
from src.services.device_service import device_service


class DeviceTable(QWidget):
    """Table widget presenting all Android devices and their live status."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._row_map: Dict[str, int] = {}  # device_id -> row_index
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header toolbar for table
        top_layout = QHBoxLayout()
        title_label = QLabel("📱 Dispositivos Android Detectados")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        self.btn_select_all = QPushButton("Seleccionar Todos")
        self.btn_select_all.setObjectName("btn-secondary")
        self.btn_select_all.clicked.connect(self._select_all)
        top_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deseleccionar")
        self.btn_deselect_all.setObjectName("btn-secondary")
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        top_layout.addWidget(self.btn_deselect_all)

        layout.addLayout(top_layout)

        # Table Widget
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Sel", "Nombre", "ID Dispositivo", "Dirección IP", "Estado", "Batería", "Última Conexión"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    def _connect_signals(self) -> None:
        event_bridge.device_registered.connect(self._on_device_registered)
        event_bridge.device_disconnected.connect(self._on_device_disconnected)
        event_bridge.device_status_updated.connect(self._on_device_status_updated)

    def _format_status_badge(self, status: str) -> str:
        status_lower = status.lower()
        if status_lower in ("connected", "idle"):
            return "🟢 Disponible"
        elif status_lower == "running":
            return "⚡ Ejecutando"
        elif status_lower == "stopped":
            return "⏹ Detenido"
        elif status_lower == "error":
            return "❌ Error"
        else:
            return "⚪ Desconectado"

    def _create_status_label(self, status: str) -> QLabel:
        lbl = QLabel(self._format_status_badge(status))
        lbl.setAlignment(Qt.AlignCenter)
        status_lower = status.lower()
        if status_lower in ("connected", "idle"):
            lbl.setStyleSheet("color: #48BB78; font-weight: bold; padding: 2px 6px;")
        elif status_lower == "running":
            lbl.setStyleSheet("color: #63B3ED; font-weight: bold; padding: 2px 6px;")
        elif status_lower == "stopped":
            lbl.setStyleSheet("color: #ECC94B; font-weight: bold; padding: 2px 6px;")
        elif status_lower == "error":
            lbl.setStyleSheet("color: #F56565; font-weight: bold; padding: 2px 6px;")
        else:
            lbl.setStyleSheet("color: #718096; padding: 2px 6px;")
        return lbl

    @Slot(dict)
    def _on_device_registered(self, dev_data: dict) -> None:
        device_id = dev_data.get("device_id")
        if not device_id:
            return

        if device_id in self._row_map:
            row = self._row_map[device_id]
        else:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._row_map[device_id] = row

            # Checkbox in column 0
            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, chk_widget)

        name_item = QTableWidgetItem(dev_data.get("name", "Android Device"))
        id_item = QTableWidgetItem(device_id)
        ip_item = QTableWidgetItem(dev_data.get("ip_address", "127.0.0.1"))
        battery = dev_data.get("battery_level")
        battery_text = f"{battery}%" if battery is not None else "--"
        battery_item = QTableWidgetItem(battery_text)
        battery_item.setTextAlignment(Qt.AlignCenter)

        now_str = datetime.now().strftime("%H:%M:%S")
        seen_item = QTableWidgetItem(now_str)
        seen_item.setTextAlignment(Qt.AlignCenter)

        self.table.setItem(row, 1, name_item)
        self.table.setItem(row, 2, id_item)
        self.table.setItem(row, 3, ip_item)
        self.table.setCellWidget(row, 4, self._create_status_label(dev_data.get("status", "connected")))
        self.table.setItem(row, 5, battery_item)
        self.table.setItem(row, 6, seen_item)

    @Slot(str)
    def _on_device_disconnected(self, device_id: str) -> None:
        if device_id in self._row_map:
            row = self._row_map[device_id]
            self.table.setCellWidget(row, 4, self._create_status_label(DeviceStatus.DISCONNECTED.value))

    @Slot(dict)
    def _on_device_status_updated(self, payload: dict) -> None:
        device_id = payload.get("device_id")
        status = payload.get("status", "")
        if device_id in self._row_map:
            row = self._row_map[device_id]
            self.table.setCellWidget(row, 4, self._create_status_label(status))
            battery = payload.get("battery")
            if battery is not None:
                battery_item = QTableWidgetItem(f"{battery}%")
                battery_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, battery_item)
            seen_item = QTableWidgetItem(datetime.now().strftime("%H:%M:%S"))
            seen_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, seen_item)

    def _select_all(self) -> None:
        for r in range(self.table.rowCount()):
            cell_widget = self.table.cellWidget(r, 0)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                if chk:
                    chk.setChecked(True)

    def _deselect_all(self) -> None:
        for r in range(self.table.rowCount()):
            cell_widget = self.table.cellWidget(r, 0)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                if chk:
                    chk.setChecked(False)

    def get_selected_device_ids(self) -> List[str]:
        """Return list of selected device_ids."""
        selected = []
        for r in range(self.table.rowCount()):
            cell_widget = self.table.cellWidget(r, 0)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    id_item = self.table.item(r, 2)
                    if id_item:
                        selected.append(id_item.text())
        return selected
