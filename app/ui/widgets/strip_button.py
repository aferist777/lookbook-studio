"""Thin vertical 'LOG' strip on the right edge (closed state of the log panel).
Half the previous width; the drawer it opens is normal size."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from ... import config, theme

STRIP_W = 16


class StripButton(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(STRIP_W)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._count = 0

    def set_count(self, n: int) -> None:
        self._count = n
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = config.CONFIG.theme
        p.fillRect(self.rect(), QColor(theme.color(t, "surface2" if self._hover else "surface")))
        p.fillRect(0, 0, 1, self.height(), QColor(theme.color(t, "border_soft")))

        p.save()
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(-90)
        f = QFont("Inter")
        f.setPointSize(7)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2.5)
        p.setFont(f)
        p.setPen(QColor(theme.color(t, "ink" if self._hover else "muted")))
        p.drawText(QRect(-self.height() // 2, -self.width() // 2, self.height(), self.width()),
                   Qt.AlignCenter, "L O G")
        p.restore()
