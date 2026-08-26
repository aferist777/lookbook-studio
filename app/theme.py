"""Qt theming for Lookbook Studio.

Four runtime-switchable themes (matching design/showcase.html), translated from the
showcase's OKLCH palette into hex for Qt QSS. The active theme is a dropdown in the
top-right corner and is persisted via config.theme / config.set_theme.
"""
from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QFont

from . import config

# display name -> key
THEME_NAMES = {"Midnight": "midnight", "Acid": "acid", "Ember": "ember", "Paper": "paper"}

THEMES: dict[str, dict] = {
    "midnight": {
        "bg": "#181a23", "surface": "#20232e", "surface2": "#272b38",
        "border": "#363b4d", "border_soft": "#2d3242",
        "ink": "#f2f3f7", "muted": "#a3a8ba",
        "primary": "#6470f0", "primary_ink": "#ffffff", "primary_soft": "#2a2e54",
        "accent": "#56c7dd", "star": "#e9be4e",
        "success": "#4fbf8b", "danger": "#e06a5c", "warn": "#e3b15a",
    },
    "acid": {
        "bg": "#15170f", "surface": "#1b1e16", "surface2": "#23271d",
        "border": "#343b2b", "border_soft": "#292f22",
        "ink": "#f1f3ee", "muted": "#a4ab9c",
        "primary": "#c8f24a", "primary_ink": "#1c2410", "primary_soft": "#2b3417",
        "accent": "#9d5ff2", "star": "#e9c24e",
        "success": "#6fd07a", "danger": "#e0584a", "warn": "#e6c15a",
    },
    "ember": {
        "bg": "#1b1813", "surface": "#211d17", "surface2": "#29241c",
        "border": "#3a3328", "border_soft": "#2f2a20",
        "ink": "#f4f1ea", "muted": "#b3a896",
        "primary": "#e68b3d", "primary_ink": "#2a1d10", "primary_soft": "#3a2c1b",
        "accent": "#51bccf", "star": "#e9be4e",
        "success": "#4fbf8b", "danger": "#e06a4c", "warn": "#e3b15a",
    },
    "paper": {
        "bg": "#ffffff", "surface": "#f8f8fb", "surface2": "#f0f1f6",
        "border": "#e2e4ec", "border_soft": "#ebecf2",
        "ink": "#2b2f3a", "muted": "#6b7180",
        "primary": "#4d47c7", "primary_ink": "#ffffff", "primary_soft": "#e7e6f7",
        "accent": "#e15a50", "star": "#d9a13a",
        "success": "#3a9d6b", "danger": "#d6473a", "warn": "#c79236",
    },
}

_QSS = """
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 13px; outline: 0; }
QWidget { background: %(bg)s; color: %(ink)s; }
QToolTip {
    background: %(ink)s; color: %(bg)s; border: 1px solid %(border)s;
    padding: 5px 8px; border-radius: 6px; font-size: 12px;
}

/* Tabs (main nav, underline style) */
QTabWidget::pane { border: 0; background: %(bg)s; }
QTabBar { qproperty-drawBase: 0; background: %(bg)s; }
QTabBar::tab {
    background: transparent; color: %(muted)s; padding: 9px 15px; margin: 2px 1px 0 1px;
    border: 0; border-bottom: 2px solid transparent; font-weight: 500;
}
QTabBar::tab:hover { color: %(ink)s; }
QTabBar::tab:selected { color: %(ink)s; border-bottom: 2px solid %(primary)s; }

/* Buttons */
QPushButton {
    background: %(surface2)s; color: %(ink)s; border: 1px solid %(border)s;
    border-radius: 8px; padding: 6px 13px; font-weight: 500;
}
QPushButton:hover { border-color: %(muted)s; }
QPushButton:pressed { background: %(surface)s; }
QPushButton:disabled { color: %(muted)s; }
QPushButton[accent="true"] {
    background: %(primary)s; color: %(primary_ink)s; border: 0; font-weight: 600;
}
QPushButton[accent="true"]:hover { background: %(primary)s; }
QPushButton[flat="true"] { background: transparent; border: 0; color: %(muted)s; }
QPushButton[flat="true"]:hover { background: %(surface2)s; color: %(ink)s; }

/* Inputs */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {
    background: %(bg)s; color: %(ink)s; border: 1px solid %(border)s;
    border-radius: 8px; padding: 6px 9px; selection-background-color: %(primary_soft)s;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid %(primary)s;
}
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid %(muted)s; margin-right: 8px; }
QComboBox QAbstractItemView {
    background: %(surface2)s; color: %(ink)s; border: 1px solid %(border)s;
    border-radius: 8px; padding: 4px; selection-background-color: %(primary_soft)s;
    selection-color: %(ink)s; outline: 0;
}

/* Cards / panels via objectName */
QFrame#panel { background: %(surface)s; border: 1px solid %(border_soft)s; border-radius: 14px; }
QLabel#title { font-size: 19px; font-weight: 600; color: %(ink)s; }
QLabel#subtle { color: %(muted)s; font-size: 12px; }
QLabel#muted { color: %(muted)s; }
QFrame#divider { background: %(border_soft)s; max-height: 1px; border: 0; }
QWidget#themePicker { min-width: 132px; }

/* Log panel */
QFrame#logDrawer { background: %(surface)s; border-left: 1px solid %(border)s; }
QLabel#logTitle { font-size: 13px; font-weight: 650; color: %(ink)s; }
QListWidget#logList { background: %(bg)s; border: 1px solid %(border_soft)s; border-radius: 8px; padding: 4px;
    font-family: "JetBrains Mono","Cascadia Code",Consolas,monospace; font-size: 11.5px; }
QListWidget#logList::item { padding: 4px 6px; border-radius: 4px; }
QListWidget#logList::item:selected { background: %(primary_soft)s; color: %(ink)s; }
QTextBrowser#logCode { background: %(bg)s; border: 1px solid %(border_soft)s; border-radius: 8px; color: %(ink)s;
    font-family: "JetBrains Mono","Cascadia Code",Consolas,monospace; font-size: 11.5px; }
QPushButton[dtab="true"] { background: transparent; border: 0; color: %(muted)s; padding: 5px 11px; border-radius: 6px; font-weight: 560; }
QPushButton[dtab="true"]:checked { color: %(ink)s; background: %(surface2)s; }

/* Splitter sashes */
QSplitter::handle { background: %(border_soft)s; }
QSplitter::handle:hover { background: %(primary)s; }
QSplitter::handle:horizontal { width: 6px; }
QSplitter::handle:vertical { height: 6px; }

/* Persona editor */
QLabel#imgPanel { background: %(surface2)s; border: 1px solid %(border_soft)s; border-radius: 10px; color: %(muted)s; }
QLabel#imgPanel[sel="true"] { border: 2px solid %(primary)s; }
QTableWidget { background: %(surface)s; border: 1px solid %(border_soft)s; border-radius: 10px; gridline-color: %(border_soft)s; }
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section { background: %(surface2)s; color: %(muted)s; border: 0; padding: 6px 8px; font-weight: 600; }
QLabel#h3 { font-size: 13px; font-weight: 600; color: %(ink)s; }
QLabel#formLabel { color: %(muted)s; font-size: 12px; }
QListWidget { background: %(surface)s; border: 1px solid %(border_soft)s; border-radius: 10px; padding: 5px; }
QListWidget::item { padding: 7px 8px; border-radius: 7px; color: %(ink)s; }
QListWidget::item:hover { background: %(surface2)s; }
QListWidget::item:selected { background: %(primary_soft)s; color: %(ink)s; }
QSpinBox { background: %(bg)s; color: %(ink)s; border: 1px solid %(border)s; border-radius: 8px; padding: 5px 8px; }
QSlider::groove:horizontal { height: 5px; background: %(surface2)s; border-radius: 3px; }
QSlider::handle:horizontal { width: 15px; height: 15px; margin: -6px 0; border-radius: 8px; background: %(primary)s; border: 3px solid %(bg)s; }

/* Product cards + segmented + pager (Wardrobe) */
QFrame#pcard { background: %(surface)s; border: 1px solid %(border_soft)s; border-radius: 11px; }
QLabel#cardThumb { background: %(surface2)s; border-radius: 8px; color: %(muted)s; }
QLabel#cardTitle { color: %(ink)s; }
QLabel#price { font-size: 15px; font-weight: 700; color: %(ink)s; }
QLabel#cardMeta { color: %(muted)s; font-size: 11px; }
QLabel#badgeSrc { color: %(success)s; background: %(surface2)s; border-radius: 5px; padding: 2px 6px; font-size: 10px; font-weight: 600; }
QLabel#status, QLabel#sectionCount { color: %(muted)s; }
QPushButton#star { background: transparent; border: 0; color: %(muted)s; font-size: 17px; padding: 0 2px; }
QPushButton#star:hover, QPushButton#star:checked { color: %(star)s; }
QWidget#segbar { background: %(surface)s; border: 1px solid %(border_soft)s; border-radius: 9px; }
QPushButton[seg="true"] { background: transparent; border: 0; color: %(muted)s; padding: 6px 15px; border-radius: 7px; font-weight: 500; }
QPushButton[seg="true"]:checked { background: %(surface2)s; color: %(ink)s; }
QPushButton[flat="true"] { background: transparent; border: 0; color: %(muted)s; padding: 5px 9px; }
QPushButton[flat="true"]:hover { color: %(ink)s; }
QPushButton[flat="true"]:disabled { color: %(border)s; }

/* Scrollbars */
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(border)s; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""

_font_loaded = False


def _ensure_font() -> None:
    global _font_loaded
    if _font_loaded:
        return
    path = config.ASSETS_DIR / "fonts" / "Inter.ttf"
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))
    _font_loaded = True


def build_qss(theme_key: str) -> str:
    return _QSS % THEMES.get(theme_key, THEMES["midnight"])


def color(theme_key: str, role: str) -> str:
    return THEMES.get(theme_key, THEMES["midnight"]).get(role, "#000000")


def apply(app, theme_key: str) -> None:
    """Apply a theme to the QApplication and set the base font."""
    _ensure_font()
    app.setFont(QFont("Inter", 9))
    app.setStyleSheet(build_qss(theme_key))
