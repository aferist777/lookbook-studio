"""Log panel — a right-edge overlay. Thin 'LOG' strip (closed) toggles a normal-size
drawer (open). Console-style list, newest on top, 30 per page with vertical scroll and
arrow paging, a 'delete oldest 30' button + total counter. Detail shows the selected
call's full Request / Response / Result JSON with clickable media links. Click the
scrim (anywhere outside the drawer) to close.
"""
from __future__ import annotations

import html
import json
import re
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget,
)

from .. import config, theme
from ..ai.log import STORE
from .widgets.strip_button import STRIP_W, StripButton

DRAWER_W = 440
PAGE = 30
_URL = re.compile(r'(https?://[^\s"<>]+)')


def _fmt_time(ts) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "--:--:--"


def _kinds(kinds) -> str:
    m = {"text": "txt", "image": "img"}
    return "+".join(m.get(k, k) for k in (kinds or [])) or "-"


def _to_html(obj) -> str:
    if isinstance(obj, str):
        text = obj
    else:
        try:
            text = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        except Exception:
            text = str(obj)
    esc = html.escape(text)
    esc = _URL.sub(r'<a href="\1">\1</a>', esc)
    return f"<pre style='white-space:pre-wrap;word-break:break-word;margin:0'>{esc}</pre>"


class LogOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._open = False
        self._page = 0
        self._sel = None
        self._dview = "request"
        self._build()
        self.strip.set_count(STORE.count())
        STORE.added.connect(self._on_change)
        STORE.updated.connect(self._on_change)
        STORE.changed.connect(self._on_change)
        self.reposition()

    # ------------------------------------------------------------- build
    def _build(self) -> None:
        self.strip = StripButton(self)
        self.strip.clicked.connect(self.toggle)

        self.drawer = QFrame(self)
        self.drawer.setObjectName("logDrawer")
        lay = QVBoxLayout(self.drawer)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(9)

        head = QHBoxLayout()
        title = QLabel("AI Log")
        title.setObjectName("logTitle")
        self.counter = QLabel("0 logs")
        self.counter.setObjectName("subtle")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.counter)
        lay.addLayout(head)

        self.list = QListWidget()
        self.list.setObjectName("logList")
        self.list.itemClicked.connect(self._on_item)
        lay.addWidget(self.list, 1)

        pager = QHBoxLayout()
        self.del_btn = QPushButton("Delete oldest 30")
        self.del_btn.setProperty("flat", True)
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setToolTip("Remove the 30 oldest log entries from memory and disk")
        self.del_btn.clicked.connect(lambda: STORE.delete_oldest(30))
        self.prev = QPushButton("◀")
        self.next = QPushButton("▶")
        for b in (self.prev, self.next):
            b.setProperty("flat", True)
            b.setCursor(Qt.PointingHandCursor)
        self.page_lbl = QLabel("1/1")
        self.page_lbl.setObjectName("subtle")
        self.prev.clicked.connect(self._prev)
        self.next.clicked.connect(self._next)
        pager.addWidget(self.del_btn)
        pager.addStretch(1)
        pager.addWidget(self.prev)
        pager.addWidget(self.page_lbl)
        pager.addWidget(self.next)
        lay.addLayout(pager)

        dt = QHBoxLayout()
        self.dbtns = {}
        for key, label in (("request", "Request"), ("response", "Response"), ("result", "Result")):
            b = QPushButton(label)
            b.setProperty("dtab", True)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._set_dview(k))
            self.dbtns[key] = b
            dt.addWidget(b)
        dt.addStretch(1)
        self.dbtns["request"].setChecked(True)
        lay.addLayout(dt)

        self.code = QTextBrowser()
        self.code.setObjectName("logCode")
        self.code.setOpenExternalLinks(True)
        lay.addWidget(self.code, 1)

    # ------------------------------------------------------------- geometry
    def reposition(self) -> None:
        par = self.parentWidget()
        if not par:
            return
        w, h = par.width(), par.height()
        if self._open:
            self.setGeometry(0, 0, w, h)
            self.drawer.setGeometry(w - STRIP_W - DRAWER_W, 0, DRAWER_W, h)
            self.drawer.show()
            self.strip.setGeometry(w - STRIP_W, 0, STRIP_W, h)
        else:
            self.setGeometry(w - STRIP_W, 0, STRIP_W, h)
            self.drawer.hide()
            self.strip.setGeometry(0, 0, STRIP_W, h)
        self.raise_()

    def paintEvent(self, e):
        if self._open:
            QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 110))

    def mousePressEvent(self, e):
        if self._open:  # click on scrim closes
            self.toggle()

    def toggle(self) -> None:
        self._open = not self._open
        self.reposition()
        if self._open:
            self._refresh()

    def refresh_theme(self) -> None:
        self.strip.update()

    # ------------------------------------------------------------- data
    def _on_change(self, *_a) -> None:
        self.strip.set_count(STORE.count())
        if self._open:
            self._refresh()

    def _refresh(self) -> None:
        items = STORE.newest_first()
        total = len(items)
        self.counter.setText(f"{total} logs")
        pages = max(1, (total + PAGE - 1) // PAGE)
        self._page = min(self._page, pages - 1)
        start = self._page * PAGE
        self.list.clear()
        for e in items[start:start + PAGE]:
            txt = f"{_fmt_time(e.ts)}  [{e.provider}]  {e.op}  ·  {_kinds(e.kinds)}  ·  {e.status}"
            it = QListWidgetItem(txt)
            it.setData(Qt.UserRole, e.id)
            role = "danger" if e.status == "error" else "warn" if e.status == "pending" else "muted"
            it.setForeground(QColor(theme.color(config.CONFIG.theme, role)))
            self.list.addItem(it)
            if e.id == self._sel:
                self.list.setCurrentItem(it)
        self.page_lbl.setText(f"{self._page + 1}/{pages}")
        self._show_detail()

    def _entry(self, eid):
        for e in STORE.newest_first():
            if e.id == eid:
                return e
        return None

    def _on_item(self, it) -> None:
        self._sel = it.data(Qt.UserRole)
        self._show_detail()

    def _set_dview(self, k) -> None:
        self._dview = k
        for key, b in self.dbtns.items():
            b.setChecked(key == k)
        self._show_detail()

    def _show_detail(self) -> None:
        e = self._entry(self._sel) if self._sel else None
        if not e:
            self.code.setHtml("")
            return
        data = e.request if self._dview == "request" else e.response if self._dview == "response" else e.result
        self.code.setHtml(_to_html(data))

    def _prev(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._refresh()

    def _next(self) -> None:
        self._page += 1
        self._refresh()
