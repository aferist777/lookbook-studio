"""Collect tab — references → vision search. Three sub-tabs:

References: embedded browser (Instagram / Pinterest), ⭐ saves the current link.
Saved links: the links (source of truth) → Download (yt-dlp) → Pick frame (popup).
Parsing: a saved frame → Analyze (V1 vision) → keyword search → star into the wardrobe.

The browser is created lazily on first show so headless/offscreen runs don't touch it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ... import collect, config, wardrobe
from ...ai import service
from ...sources.base import get_source
from ...workers import run_async
from ..widgets.frame_dialog import FrameDialog
from ..widgets.model_selector import ModelSelector
from ..widgets.product_card import ProductCard


def _h3(text) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("h3")
    return lb


# ===================================================================== References
class ReferencesTab(QWidget):
    def __init__(self, on_saved):
        super().__init__()
        self._on_saved = on_saved
        self._web = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(9)

        bar = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItems(["Instagram", "Pinterest"])
        self.source.setToolTip("Reference source")
        self.query = QLineEdit()
        self.query.setPlaceholderText("Pinterest search query")
        open_btn = QPushButton("Open")
        open_btn.setToolTip("Open the source (Instagram reels / Pinterest search)")
        open_btn.clicked.connect(self._open_source)
        self.addr = QLineEdit()
        self.addr.setPlaceholderText("https://…")
        go = QPushButton("Go")
        go.clicked.connect(self._go)
        star = QPushButton("★ Save link")
        star.setProperty("accent", True)
        star.setCursor(Qt.PointingHandCursor)
        star.setToolTip("Save the current page link to Saved links")
        star.clicked.connect(self._save_link)
        bar.addWidget(self.source)
        bar.addWidget(self.query, 1)
        bar.addWidget(open_btn)
        bar.addWidget(self.addr, 1)
        bar.addWidget(go)
        bar.addWidget(star)
        lay.addLayout(bar)

        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_lay.setContentsMargins(0, 0, 0, 0)
        self.placeholder = QLabel("The browser loads when this tab is opened. Log in once — cookies persist.")
        self.placeholder.setObjectName("status")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.host_lay.addWidget(self.placeholder)
        lay.addWidget(self.host, 1)

        note = QLabel("Tip: use a dedicated burner IG account. Manual ingest: drop images into data/cache.")
        note.setObjectName("subtle")
        lay.addWidget(note)

    def showEvent(self, e):
        super().showEvent(e)
        self._ensure_web()

    def _ensure_web(self):
        if self._web is not None:
            return
        try:
            from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._profile = QWebEngineProfile("lookbook", self)
            self._profile.setPersistentStoragePath(str(config.DATA_DIR / "webprofile"))
            self._profile.setHttpUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
            self._web = QWebEngineView(self)
            self._web.setPage(QWebEnginePage(self._profile, self._web))
            self._web.urlChanged.connect(lambda u: self.addr.setText(u.toString()))
            self.placeholder.hide()
            self.host_lay.addWidget(self._web)
            self._open_source()
        except Exception as ex:
            self.placeholder.setText(f"Embedded browser unavailable: {ex}")

    def _open_source(self):
        if not self._web:
            return
        from PySide6.QtCore import QUrl
        if self.source.currentText() == "Pinterest":
            q = self.query.text().strip().replace(" ", "%20")
            url = f"https://www.pinterest.com/search/pins/?q={q}" if q else "https://www.pinterest.com/"
        else:
            url = "https://www.instagram.com/reels/"
        self._web.setUrl(QUrl(url))

    def _go(self):
        if not self._web:
            return
        from PySide6.QtCore import QUrl
        u = self.addr.text().strip()
        if u and not u.startswith("http"):
            u = "https://" + u
        if u:
            self._web.setUrl(QUrl(u))

    def _save_link(self):
        url = self._web.url().toString() if self._web else self.addr.text().strip()
        if not url:
            return
        collect.save_link(url, self.source.currentText().lower())
        self._on_saved()


# ===================================================================== Saved links
class SavedLinksTab(QWidget):
    def __init__(self, open_frame):
        super().__init__()
        self._open_frame = open_frame
        self._links = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(9)

        bar = QHBoxLayout()
        self.count = QLabel("0 links")
        self.count.setObjectName("subtle")
        refresh = QPushButton("Refresh")
        refresh.setProperty("flat", True)
        refresh.clicked.connect(self.reload)
        dl = QPushButton("Download")
        dl.setProperty("accent", True)
        dl.setToolTip("Download media for the selected link (yt-dlp)")
        dl.clicked.connect(self._download)
        frame = QPushButton("Pick frame")
        frame.setToolTip("Open the frame picker for the downloaded video")
        frame.clicked.connect(self._pick_frame)
        delete = QPushButton("Delete")
        delete.setProperty("flat", True)
        delete.clicked.connect(self._delete)
        bar.addWidget(self.count)
        bar.addStretch(1)
        for b in (refresh, dl, frame, delete):
            b.setCursor(Qt.PointingHandCursor)
            bar.addWidget(b)
        lay.addLayout(bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source", "URL", "Status", "Media"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        lay.addWidget(self.table, 1)

        self.status = QLabel("")
        self.status.setObjectName("status")
        lay.addWidget(self.status)
        self.reload()

    def reload(self):
        self._links = collect.list_links()
        self.table.setRowCount(len(self._links))
        for r, l in enumerate(self._links):
            media = Path(l["media_path"]).name if l.get("media_path") else ""
            for c, val in enumerate((l.get("source", ""), l.get("url", ""), l.get("status", ""), media)):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.count.setText(f"{len(self._links)} links")

    def _selected(self):
        r = self.table.currentRow()
        return self._links[r] if 0 <= r < len(self._links) else None

    def _download(self):
        l = self._selected()
        if not l:
            self.status.setText("Select a link.")
            return
        self.status.setText("Downloading…")
        run_async(collect.download_media, lambda _p: self._after_dl(), lambda e: self.status.setText(e),
                  l["url"], l["id"])

    def _after_dl(self):
        self.status.setText("Downloaded.")
        self.reload()

    def _pick_frame(self):
        l = self._selected()
        if not l or not l.get("media_path"):
            self.status.setText("Download the media first.")
            return
        self._open_frame(l["media_path"], l["id"])

    def _delete(self):
        l = self._selected()
        if l:
            collect.delete_link(l["id"])
            self.reload()


# ===================================================================== Parsing
class ParsingTab(QWidget):
    def __init__(self):
        super().__init__()
        self._frame = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(9)
        left.addWidget(_h3("Frame"))
        self.frame_img = QLabel("no frame")
        self.frame_img.setObjectName("imgPanel")
        self.frame_img.setFixedSize(210, 300)
        self.frame_img.setAlignment(Qt.AlignCenter)
        left.addWidget(self.frame_img)
        self.analyze_btn = QPushButton("Analyze (V1) → search")
        self.analyze_btn.setProperty("accent", True)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setToolTip("Identify garments and search AliExpress for each")
        self.analyze_btn.clicked.connect(self._analyze)
        left.addWidget(self.analyze_btn)
        left.addWidget(ModelSelector("V1"))
        left.addStretch(1)
        leftw = QWidget()
        leftw.setLayout(left)
        leftw.setFixedWidth(240)
        lay.addWidget(leftw)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.status = QLabel("Pick a frame in Saved links, then analyze.")
        self.status.setObjectName("status")
        right.addWidget(self.status)
        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        right.addWidget(host, 1)
        rightw = QWidget()
        rightw.setLayout(right)
        lay.addWidget(rightw, 1)

    def set_frame(self, path):
        self._frame = path
        if path and Path(path).exists():
            self.frame_img.setPixmap(QPixmap(path).scaled(210, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status.setText("Frame ready — Analyze to find products.")

    def _analyze(self):
        if not self._frame:
            self.status.setText("No frame selected.")
            return
        self.status.setText("Analyzing frame…")
        self.analyze_btn.setEnabled(False)
        run_async(self._search, self._on_results, self._on_error, self._frame)

    @staticmethod
    def _search(frame_path):
        items = service.analyze_reference(frame_path)
        src = get_source("aliexpress_keyword")
        results = []
        for it in items[:4]:
            q = it.get("search_query") or it.get("category")
            if not q:
                continue
            try:
                results.extend(src.search(q, page=1, page_size=6))
            except Exception:
                pass
        return results

    def _on_results(self, results):
        self.analyze_btn.setEnabled(True)
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        for i, r in enumerate(results or []):
            card = r.to_card()
            w = ProductCard(card, starred=wardrobe.is_saved(card.get("product_id")))
            w.starToggled.connect(self._star)
            self.grid.addWidget(w, i // 5, i % 5)
        self.status.setText(f"{len(results or [])} matches — star to add to the wardrobe.")

    def _star(self, card, checked):
        if checked:
            run_async(wardrobe.save_result, None, None, card)
        else:
            run_async(wardrobe.delete_by_product, None, None, card.get("product_id"), card.get("source", "aliexpress"))

    def _on_error(self, msg):
        self.analyze_btn.setEnabled(True)
        self.status.setText(msg)


# ===================================================================== Collect
class CollectTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        sub = QTabWidget()
        sub.setProperty("subtabs", True)
        self.refs = ReferencesTab(self._on_link_saved)
        self.saved = SavedLinksTab(self._open_frame)
        self.parsing = ParsingTab()
        sub.addTab(self.refs, "References")
        sub.addTab(self.saved, "Saved links")
        sub.addTab(self.parsing, "Parsing")
        lay.addWidget(sub)

    def _on_link_saved(self):
        self.saved.reload()

    def _open_frame(self, video_path, link_id):
        dlg = FrameDialog(video_path, link_id, self)
        if dlg.exec() and dlg.saved_path:
            self.parsing.set_frame(dlg.saved_path)
