"""Tabler icon loader → QIcon (loads SVGs from assets/icons/tabler/)."""
from __future__ import annotations

from PySide6.QtGui import QIcon

from . import config

_cache: dict[str, QIcon] = {}


def icon(name: str) -> QIcon:
    """QIcon for the Tabler icon `name` (without .svg). Empty QIcon if not vendored."""
    if name in _cache:
        return _cache[name]
    path = config.ICONS_DIR / f"{name}.svg"
    ic = QIcon(str(path)) if path.exists() else QIcon()
    _cache[name] = ic
    return ic
