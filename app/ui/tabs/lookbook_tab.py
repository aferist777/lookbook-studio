"""Lookbook tab — assemble & publish (MVP).

Pick a lookbook draft (from the Fitting room) → build the collage (flatlay / hybrid /
full-AI) → edit the post template → export a ready-to-post package (model shot + collage
+ caption + affiliate links). One outfit = one lookbook.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from ... import collage, lookbooks
from ...workers import run_async
from ..widgets.model_selector import ModelSelector

ENGINES = [("flatlay", "Flatlay (template)"), ("hybrid", "Hybrid (AI bg)"), ("poster", "Poster (model + items)")]


class LookbookTab(QWidget):
    def __init__(self):
        super().__init__()
        self._lb_id = None
        self._lb = None

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(16)
        root.addWidget(self._build_left())
        root.addWidget(self._build_right(), 1)
        self.reload()

    # ------------------------------------------------------------- left
    def _build_left(self) -> QWidget:
        box = QWidget()
        box.setFixedWidth(280)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        head = QHBoxLayout()
        title = QLabel("Lookbooks")
        title.setObjectName("h3")
        refresh = QPushButton("Refresh")
        refresh.setProperty("flat", True)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self.reload)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(refresh)
        lay.addLayout(head)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_pick)
        lay.addWidget(self.list, 1)
        self.count_lbl = QLabel("0 lookbooks")
        self.count_lbl.setObjectName("subtle")
        lay.addWidget(self.count_lbl)
        return box

    # ------------------------------------------------------------- right
    def _build_right(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        imgs = QHBoxLayout()
        imgs.setSpacing(14)
        self.model_img = self._panel("model shot")
        self.collage_img = self._panel("collage")
        imgs.addWidget(self._titled("Model", self.model_img))
        imgs.addWidget(self._titled("Collage", self.collage_img))
        imgs.addStretch(1)
        lay.addLayout(imgs)

        row = QHBoxLayout()
        row.setSpacing(9)
        self.engine = QComboBox()
        for eid, label in ENGINES:
            self.engine.addItem(label, eid)
        self.engine.setToolTip("Collage engine")
        self.build_btn = QPushButton("Build collage")
        self.build_btn.setCursor(Qt.PointingHandCursor)
        self.build_btn.setToolTip("Compose the product collage")
        self.build_btn.clicked.connect(self._build_collage)
        row.addWidget(QLabel("Collage"))
        row.addWidget(self.engine)
        row.addWidget(ModelSelector("G9"))
        row.addWidget(self.build_btn)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addWidget(self._titled_label("Post template  ·  {persona} and {items} are substituted"))
        self.template = QPlainTextEdit()
        self.template.setPlainText(lookbooks.DEFAULT_TEMPLATE)
        self.template.setFixedHeight(150)
        lay.addWidget(self.template)

        foot = QHBoxLayout()
        self.status = QLabel("Pick a lookbook draft from the left.")
        self.status.setObjectName("status")
        self.open_btn = QPushButton("Open folder")
        self.open_btn.setProperty("flat", True)
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self._open_folder)
        tg = QPushButton("Post to Telegram")
        tg.setCursor(Qt.PointingHandCursor)
        tg.setToolTip("Publish the collage + caption to your Telegram channel (Bot API)")
        tg.clicked.connect(self._post_telegram)
        export = QPushButton("Export package")
        export.setProperty("accent", True)
        export.setCursor(Qt.PointingHandCursor)
        export.setToolTip("Write model + collage + caption + affiliate links to a folder")
        export.clicked.connect(self._export)
        foot.addWidget(self.status)
        foot.addStretch(1)
        foot.addWidget(self.open_btn)
        foot.addWidget(tg)
        foot.addWidget(export)
        lay.addLayout(foot)
        lay.addStretch(1)
        return box

    def _panel(self, text) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("imgPanel")
        lb.setFixedSize(220, 270)
        lb.setAlignment(Qt.AlignCenter)
        return lb

    def _titled(self, title, widget) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._titled_label(title))
        v.addWidget(widget)
        return w

    def _titled_label(self, text) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("h3")
        return lb

    # ------------------------------------------------------------- data
    def reload(self) -> None:
        self.list.clear()
        rows = lookbooks.list_all()
        for r in rows:
            label = f"{r.get('name') or 'Lookbook'}  ·  {r.get('persona_name') or '—'}"
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, r["id"])
            self.list.addItem(it)
        self.count_lbl.setText(f"{len(rows)} lookbooks")

    def _on_pick(self, it) -> None:
        self._load(it.data(Qt.UserRole))

    def _load(self, lb_id) -> None:
        self._lb_id = lb_id
        self._lb = lookbooks.get(lb_id)
        if not self._lb:
            return
        self._show(self.model_img, self._lb.get("model_shot_path"), "model shot")
        self._show(self.collage_img, self._lb.get("collage_path"), "collage")
        if self._lb.get("post_text"):
            self.template.setPlainText(self._lb["post_text"])
        eng = self._lb.get("collage_engine")
        if eng:
            i = self.engine.findData(eng)
            if i >= 0:
                self.engine.setCurrentIndex(i)
        self.status.setText(f"Loaded “{self._lb.get('name')}” ({len(self._lb.get('items', []))} items).")

    def _show(self, label, path, placeholder) -> None:
        if path and Path(path).exists():
            label.setPixmap(QPixmap(path).scaled(label.width(), label.height(),
                                                 Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            label.clear()
            label.setText(placeholder)

    # ------------------------------------------------------------- actions
    def _build_collage(self) -> None:
        if not self._lb:
            self.status.setText("Pick a lookbook first.")
            return
        engine = self.engine.currentData()
        self.status.setText(f"Building {engine} collage…")
        self.build_btn.setEnabled(False)
        run_async(collage.build, self._on_collage, self._on_error, self._lb, engine)

    def _on_collage(self, path) -> None:
        self.build_btn.setEnabled(True)
        lookbooks.update_collage(self._lb_id, path, self.engine.currentData())
        self._lb["collage_path"] = path
        self._show(self.collage_img, path, "collage")
        self.status.setText("Collage built.")

    def _on_error(self, msg) -> None:
        self.build_btn.setEnabled(True)
        self.status.setText(msg)

    def _export(self) -> None:
        if not self._lb_id:
            self.status.setText("Pick a lookbook first.")
            return
        tmpl = self.template.toPlainText()
        lookbooks.update_post(self._lb_id, tmpl)
        lb = lookbooks.get(self._lb_id)
        try:
            out = lookbooks.export_package(lb, tmpl)
        except Exception as e:
            self.status.setText(str(e))
            return
        self._export_dir = out
        self.status.setText(f"Exported → {out}")

    def _post_telegram(self) -> None:
        if not self._lb_id:
            self.status.setText("Pick a lookbook first.")
            return
        lb = lookbooks.get(self._lb_id)
        caption = lookbooks.render_post(lb, self.template.toPlainText())
        self.status.setText("Posting to Telegram…")
        run_async(lookbooks.post_to_telegram, lambda _r: self.status.setText("Posted to Telegram."),
                  lambda e: self.status.setText(e), lb, caption)

    def _open_folder(self) -> None:
        d = getattr(self, "_export_dir", None) or (self._lb or {}).get("export_dir")
        if d and Path(d).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        else:
            self.status.setText("Nothing exported yet.")
