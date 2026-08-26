"""Shared helpers for tab widgets."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderTab(QWidget):
    """Scaffold tab: title, build-phase subtitle, and a bullet list of what it will do.
    Replaced with real UI as each phase is implemented. Designed to fit without
    vertical scrolling (the app has no page-level scroll for now)."""

    def __init__(self, title: str, phase: str, bullets: list[str]):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(8)

        h = QLabel(title)
        h.setObjectName("title")
        root.addWidget(h)

        sub = QLabel(phase)
        sub.setObjectName("subtle")
        root.addWidget(sub)

        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.HLine)
        root.addWidget(line)
        root.addSpacing(6)

        for b in bullets:
            lb = QLabel("•   " + b)
            lb.setWordWrap(True)
            lb.setTextFormat(Qt.PlainText)
            root.addWidget(lb)

        root.addStretch(1)
