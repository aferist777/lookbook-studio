"""Fitting room — virtual try-on.

Pick a persona + build an outfit from wardrobe items (per-item slot + on-model/collage
mode) → generate a batch of layered try-on passes → pick the best → Accept sends it to
the Lookbook as a draft. Try-on uses G5/G6/G7 (cutouts via U1); all calls are logged.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ... import fitting, lookbooks, personas, wardrobe
from ...workers import run_async
from ..widgets.model_selector import ModelSelector

SLOTS = ["top", "bottom", "footwear", "outerwear", "headwear", "accessory"]


class ClickableThumb(QLabel):
    clicked = Signal(int)

    def __init__(self, path, idx, w=152, h=196):
        super().__init__()
        self.idx = idx
        self.setObjectName("imgPanel")
        self.setFixedSize(w, h)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        if path and Path(path).exists():
            self.setPixmap(QPixmap(path).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText("result")

    def mousePressEvent(self, e):
        self.clicked.emit(self.idx)

    def set_selected(self, on: bool):
        self.setProperty("sel", on)
        self.style().unpolish(self)
        self.style().polish(self)


class FittingRoomTab(QWidget):
    def __init__(self):
        super().__init__()
        self._persona = None
        self._results: list[str] = []
        self._thumbs: list[ClickableThumb] = []
        self._selected = -1

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(16)
        root.addWidget(self._build_left())
        root.addWidget(self._build_right(), 1)

        self._reload_personas()
        self._reload_outfit()

    # ------------------------------------------------------------- left
    def _build_left(self) -> QWidget:
        box = QWidget()
        box.setFixedWidth(320)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)

        lay.addWidget(self._h("Persona"))
        self.persona_cb = QComboBox()
        self.persona_cb.setToolTip("Persona to dress (needs a full-body anchor)")
        self.persona_cb.currentIndexChanged.connect(self._on_persona)
        lay.addWidget(self.persona_cb)

        self.persona_img = QLabel("—")
        self.persona_img.setObjectName("imgPanel")
        self.persona_img.setFixedHeight(196)
        self.persona_img.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.persona_img)

        lay.addWidget(self._h("Outfit"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Use", "Item", "Slot", "Mode"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (0, 2, 3):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        lay.addWidget(self.table, 1)
        return box

    # ------------------------------------------------------------- right
    def _build_right(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        controls = QHBoxLayout()
        controls.setSpacing(9)
        controls.addWidget(QLabel("Batch"))
        self.batch = QSpinBox()
        self.batch.setRange(1, 8)
        self.batch.setValue(4)
        self.batch.setToolTip("How many try-on variants to generate")
        controls.addWidget(self.batch)
        controls.addWidget(QLabel("Try-on"))
        controls.addWidget(ModelSelector("G5"))
        controls.addWidget(QLabel("Cutout"))
        controls.addWidget(ModelSelector("U1"))
        self.gen_btn = QPushButton("Generate batch")
        self.gen_btn.setProperty("accent", True)
        self.gen_btn.setCursor(Qt.PointingHandCursor)
        self.gen_btn.setToolTip("Generate the try-on batch (layered top → bottom → shoes)")
        self.gen_btn.clicked.connect(self._generate)
        controls.addWidget(self.gen_btn)
        controls.addStretch(1)
        lay.addLayout(controls)

        self.status = QLabel("Pick a persona, tick outfit items, then generate.")
        self.status.setObjectName("status")
        lay.addWidget(self.status)

        host = QWidget()
        self.grid = QGridLayout(host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lay.addWidget(host, 1)

        foot = QHBoxLayout()
        self.sel_lbl = QLabel("No result selected.")
        self.sel_lbl.setObjectName("status")
        self.accept_btn = QPushButton("Accept → Lookbook")
        self.accept_btn.setProperty("accent", True)
        self.accept_btn.setCursor(Qt.PointingHandCursor)
        self.accept_btn.setToolTip("Send the selected look to the Lookbook as a draft")
        self.accept_btn.clicked.connect(self._accept)
        foot.addWidget(self.sel_lbl)
        foot.addStretch(1)
        foot.addWidget(self.accept_btn)
        lay.addLayout(foot)
        return box

    # ------------------------------------------------------------- data
    def _h(self, text) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("h3")
        return lb

    def _reload_personas(self) -> None:
        self.persona_cb.blockSignals(True)
        self.persona_cb.clear()
        for p in personas.list_all():
            self.persona_cb.addItem(p["name"] or f"Persona {p['id']}", p)
        self.persona_cb.blockSignals(False)
        self._on_persona()

    def _on_persona(self) -> None:
        self._persona = self.persona_cb.currentData()
        path = (self._persona or {}).get("fullbody_path")
        if path and Path(path).exists():
            self.persona_img.setPixmap(QPixmap(path).scaled(
                self.persona_img.width(), 196, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.persona_img.clear()
            self.persona_img.setText("no full-body\nanchor")

    def _reload_outfit(self) -> None:
        items = wardrobe.list_items(200, 0)
        self.table.setRowCount(len(items))
        self._rows = []
        for r, it in enumerate(items):
            use = QTableWidgetItem()
            use.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            use.setCheckState(Qt.Unchecked)
            self.table.setItem(r, 0, use)
            title = QTableWidgetItem((it.get("title") or "")[:46])
            title.setToolTip(it.get("title") or "")
            self.table.setItem(r, 1, title)
            slot = QComboBox()
            slot.addItems(SLOTS)
            if it.get("slot") in SLOTS:
                slot.setCurrentText(it["slot"])
            self.table.setCellWidget(r, 2, slot)
            mode = QComboBox()
            mode.addItems(["On model", "Collage only"])
            self.table.setCellWidget(r, 3, mode)
            self._rows.append((it, use, slot, mode))

    def _collect_outfit(self):
        on_model, collage = [], []
        for it, use, slot, mode in self._rows:
            if use.checkState() != Qt.Checked:
                continue
            item = {**it, "slot": slot.currentText()}
            (on_model if mode.currentText() == "On model" else collage).append(item)
        return on_model, collage

    # ------------------------------------------------------------- actions
    def _generate(self) -> None:
        if not self._persona:
            self.status.setText("Create and pick a persona first.")
            return
        fullbody = self._persona.get("fullbody_path")
        if not fullbody or not Path(fullbody).exists():
            self.status.setText("This persona has no full-body anchor — generate one in Personas.")
            return
        on_model, _ = self._collect_outfit()
        if not on_model:
            self.status.setText("Tick at least one on-model item.")
            return
        self._outfit = self._collect_outfit()
        n = self.batch.value()
        self.status.setText(f"Generating {n} try-on variants… (layered)")
        self.gen_btn.setEnabled(False)
        run_async(fitting.run_batch, self._on_results, self._on_error, fullbody, on_model, n)

    def _on_results(self, paths) -> None:
        self.gen_btn.setEnabled(True)
        self._results = paths or []
        self._render_results()
        self.status.setText(f"{len(self._results)} variants ready — pick the best.")

    def _on_error(self, msg) -> None:
        self.gen_btn.setEnabled(True)
        self.status.setText(msg)

    def _render_results(self) -> None:
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._thumbs = []
        self._selected = -1
        self.sel_lbl.setText("No result selected.")
        for i, path in enumerate(self._results):
            t = ClickableThumb(path, i)
            t.clicked.connect(self._pick)
            self.grid.addWidget(t, i // 5, i % 5)
            self._thumbs.append(t)

    def _pick(self, idx) -> None:
        self._selected = idx
        for i, t in enumerate(self._thumbs):
            t.set_selected(i == idx)
        self.sel_lbl.setText(f"Selected variant {idx + 1}.")

    def _accept(self) -> None:
        if self._selected < 0 or self._selected >= len(self._results):
            self.status.setText("Pick a result first.")
            return
        on_model, collage = getattr(self, "_outfit", ([], []))
        name = (self._persona.get("name") or "Look") + " look"
        lb = lookbooks.create(self._persona.get("id"), name)
        lookbooks.set_model_shot(lb, self._results[self._selected])
        for it in on_model:
            lookbooks.add_item(lb, it["id"], "on_model")
        for it in collage:
            lookbooks.add_item(lb, it["id"], "collage_only")
        self.status.setText(f"Sent to Lookbook (draft #{lb}).")
