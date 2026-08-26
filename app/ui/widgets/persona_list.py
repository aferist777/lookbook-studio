"""Persona library list: face thumbnail per row, name, and a hover preview
(enlarged image via rich tooltip)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from ... import personas


class PersonaList(QListWidget):
    selected = Signal(int)  # persona id

    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(34, 34))
        self.setSpacing(2)
        self.setUniformItemSizes(False)
        self.itemClicked.connect(self._on_click)

    def reload(self, select_id: int | None = None) -> None:
        self.clear()
        for p in personas.list_all():
            label = p["name"] or f"Persona {p['id']}"
            traits = p.get("traits") or {}
            sub = traits.get("gender") or ""
            text = f"{label}" + (f"  ·  {sub}" if sub else "")
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p["id"])
            thumb = p.get("thumb_path") or p.get("face_path")
            if thumb and Path(thumb).exists():
                item.setIcon(QIcon(thumb))
            preview = p.get("fullbody_path") or thumb
            if preview and Path(preview).exists():
                item.setToolTip(f"<img src='{Path(preview).as_uri()}' width='150'>")
            self.addItem(item)
            if select_id is not None and p["id"] == select_id:
                self.setCurrentItem(item)

    def _on_click(self, item: QListWidgetItem) -> None:
        pid = item.data(Qt.UserRole)
        if pid is not None:
            self.selected.emit(int(pid))
