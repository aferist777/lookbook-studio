from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QMainWindow, QPushButton, QTabWidget, QWidget,
)

from .. import config, theme
from ..icons import icon
from .log_panel import LogOverlay
from .tabs.collect_tab import CollectTab
from .tabs.fitting_room_tab import FittingRoomTab
from .tabs.lookbook_tab import LookbookTab
from .tabs.personas_tab import PersonasTab
from .tabs.wardrobe_tab import WardrobeTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lookbook Studio")

        tabs = QTabWidget()
        tabs.setIconSize(QSize(17, 17))
        tabs.setDocumentMode(True)
        tabs.setMovable(False)

        # UI order: Personas · Wardrobe · Fitting room · Collect · Lookbook
        tabs.addTab(PersonasTab(), icon("user"), "Personas")
        tabs.addTab(WardrobeTab(), icon("hanger"), "Wardrobe")
        tabs.addTab(FittingRoomTab(), icon("shirt"), "Fitting room")
        tabs.addTab(CollectTab(), icon("browser"), "Collect")
        tabs.addTab(LookbookTab(), icon("layout-grid"), "Lookbook")

        tabs.setCornerWidget(self._build_theme_picker(), Qt.TopRightCorner)
        self.setCentralWidget(tabs)

        # AI log panel — right-edge overlay (thin strip when closed)
        self.log_overlay = LogOverlay(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "log_overlay"):
            self.log_overlay.reposition()

    def showEvent(self, e):
        super().showEvent(e)
        if hasattr(self, "log_overlay"):
            self.log_overlay.reposition()
            self.log_overlay.raise_()

    def _build_theme_picker(self) -> QWidget:
        self._theme = QComboBox()
        self._theme.setObjectName("themePicker")
        self._theme.setToolTip("Color theme — applies instantly, saved between sessions")
        for name, key in theme.THEME_NAMES.items():
            self._theme.addItem(name, key)
        idx = self._theme.findData(config.CONFIG.theme)
        if idx >= 0:
            self._theme.setCurrentIndex(idx)
        self._theme.currentIndexChanged.connect(self._on_theme)

        gear = QPushButton("⚙")
        gear.setObjectName("gearBtn")
        gear.setToolTip("Settings — API keys")
        gear.setCursor(Qt.PointingHandCursor)
        gear.setFixedWidth(32)
        gear.clicked.connect(self._open_settings)

        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 10, 0)
        lay.setSpacing(6)
        lay.addWidget(gear)
        lay.addWidget(self._theme)
        return holder

    def _open_settings(self) -> None:
        from .settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    def _on_theme(self) -> None:
        key = self._theme.currentData()
        theme.apply(QApplication.instance(), key)
        config.CONFIG.set_theme(key)
        if hasattr(self, "log_overlay"):
            self.log_overlay.refresh_theme()
