"""Modern Dark Theme stylesheet for PySide6 application."""

DARK_THEME = """
QWidget {
    background-color: #121418;
    color: #E2E8F0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Header & Cards */
QGroupBox {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 8px;
    margin-top: 24px;
    padding-top: 16px;
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

/* Line Edits & Spin Boxes */
QLineEdit, QSpinBox, QComboBox {
    background-color: #242933;
    border: 1px solid #3E4C5E;
    border-radius: 6px;
    padding: 8px 12px;
    color: #F7FAFC;
    selection-background-color: #3182CE;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4299E1;
    background-color: #2A303C;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Buttons */
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

QPushButton:pressed {
    background-color: #2B6CB0;
}

QPushButton:disabled {
    background-color: #2D3748;
    color: #718096;
}

/* Action Buttons */
QPushButton#btn-start {
    background-color: #2E7D32;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 20px;
}
QPushButton#btn-start:hover {
    background-color: #388E3C;
}

QPushButton#btn-stop {
    background-color: #C62828;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 20px;
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

/* Tables */
QTableWidget {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 8px;
    gridline-color: #2D3748;
    selection-background-color: #2D3748;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #242933;
    color: #A0AEC0;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #2D3748;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #232832;
}

QTableWidget::item:selected {
    background-color: #2B3545;
}

/* Checkboxes & Radio */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #E2E8F0;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #4A5568;
    background-color: #242933;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #3182CE;
    border-color: #63B3ED;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #1A1D24;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #4A5568;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: #718096;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Log Console */
QPlainTextEdit#log-console {
    background-color: #0F1115;
    color: #A0AEC0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 8px;
}
"""
