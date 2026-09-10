"""Application bootstrap and entry point."""

import sys
from PySide6.QtWidgets import QApplication
from src.core.logger import logger
from src.server.server_thread import server_thread
from src.ui.main_window import MainWindow
from src.ui.styles.theme import DARK_THEME


def main():
    """Start the BotVistas PC application."""
    # 1. Initialize Qt Application
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(DARK_THEME)

    logger.info("Initializing BotVistas PC Server and Control Panel...")

    # 2. Start the local FastAPI server used for USB stream delivery
    server_thread.start()

    # 3. Create & show main window
    window = MainWindow()
    window.show()

    logger.info("Application UI ready.")

    # 4. Run Qt Event Loop
    exit_code = qt_app.exec()

    # 5. Clean shutdown
    server_thread.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
