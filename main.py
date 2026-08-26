"""Lookbook Studio — entry point."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app import config, theme
from app.db import init_db
from app.ui.main_window import MainWindow


def main() -> None:
    config.ensure_dirs()
    init_db()

    # Required for the embedded QtWebEngine browser (Collect tab)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("Lookbook Studio")
    app.setOrganizationName("Lookbook Studio")
    theme.apply(app, config.CONFIG.theme)

    win = MainWindow()
    win.showMaximized()  # open full-screen by default
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
