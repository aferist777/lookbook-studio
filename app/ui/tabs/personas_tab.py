"""Personas tab — parameter-driven model generator.

LEFT: model library (kept). CENTER: resizable preview (right + bottom sashes) over a
bottom panel. RIGHT: name + 3 parameter groups (Main / Auxiliary / Extra) that reflow
1/2/3 columns as the panel is resized, rnd/rst helpers, collapsible prompt preview,
and Generate + Save at the very bottom. params → template → realism (RC) → G1.
"""
from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from ... import personas
from ...ai import prompts
from ...workers import run_async
from ..widgets.model_selector import ModelSelector
from ..widgets.persona_list import PersonaList


class _ResizePanel(QWidget):
    """Right params panel that reports its width so the grids can reflow columns."""

    def __init__(self, on_resize):
        super().__init__()
        self._on_resize = on_resize

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._on_resize(self.width())


class PersonasTab(QWidget):
    def __init__(self):
        super().__init__()
        self._cur = {"id": None, "image": None}
        self._grids = []   # [(QGridLayout, [field widgets])]
        self._cols = 2

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(12)
        root.addWidget(self._build_library())

        self._hsplit = QSplitter(Qt.Horizontal)
        self._hsplit.setChildrenCollapsible(False)
        self._hsplit.addWidget(self._build_center())
        self._hsplit.addWidget(self._build_params())
        self._hsplit.setStretchFactor(0, 1)
        self._hsplit.setSizes([760, 340])
        root.addWidget(self._hsplit, 1)

        self.library.reload()
        self._refresh_count()
        self._update_preview()

    # ------------------------------------------------------------- LEFT
    def _build_library(self) -> QWidget:
        box = QWidget()
        box.setFixedWidth(240)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        new_btn = QPushButton("+  New")
        new_btn.setProperty("accent", True)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._new)
        lay.addWidget(new_btn)
        self.library = PersonaList()
        self.library.selected.connect(self._load)
        lay.addWidget(self.library, 1)
        self.count_lbl = QLabel("0 models")
        self.count_lbl.setObjectName("formLabel")
        lay.addWidget(self.count_lbl)
        return box

    # ------------------------------------------------------------- CENTER (vertical splitter)
    def _build_center(self) -> QWidget:
        vsplit = QSplitter(Qt.Vertical)
        vsplit.setChildrenCollapsible(False)
        self.preview = QLabel("No model yet\nset parameters, then generate")
        self.preview.setObjectName("imgPanel")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(220)

        bottom = QWidget()
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(0, 6, 0, 0)
        bv.setSpacing(4)
        self.status = QLabel("Set parameters and press Generate.")
        self.status.setObjectName("status")
        hint = QLabel("Generated variants and history will appear here.")
        hint.setObjectName("formLabel")
        bv.addWidget(self.status)
        bv.addWidget(hint)
        bv.addStretch(1)

        vsplit.addWidget(self.preview)
        vsplit.addWidget(bottom)
        vsplit.setStretchFactor(0, 1)
        vsplit.setSizes([520, 96])
        return vsplit

    # ------------------------------------------------------------- RIGHT (params)
    def _build_params(self) -> QWidget:
        panel = _ResizePanel(self._on_params_resize)
        panel.setMinimumWidth(224)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lay.addWidget(QLabel("Name"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("model name, e.g. Mika")
        lay.addWidget(self.name)

        hdr = QHBoxLayout()
        hdr.addWidget(self._h3("Parameters"))
        hdr.addStretch(1)
        rnd = QPushButton("rnd"); rnd.setToolTip("Randomize Main + Auxiliary fields")
        rst = QPushButton("rst"); rst.setToolTip("Reset all fields")
        for b in (rnd, rst):
            b.setProperty("flat", True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedWidth(38)
        rnd.clicked.connect(self._rnd)
        rst.clicked.connect(self._rst)
        hdr.addWidget(rnd)
        hdr.addWidget(rst)
        lay.addLayout(hdr)

        self.age = self._combo(prompts.AGE_PRESETS)
        self.gender = self._combo(prompts.GENDER_PRESETS)
        self.pose = self._combo(prompts.POSE_PRESETS)
        self.expr = self._combo(prompts.EMOTION_PRESETS)
        self.body = self._combo(prompts.BODY_PRESETS)
        self.skin = self._combo(prompts.SKIN_PRESETS)
        self.hair = self._combo(prompts.HAIR_PRESETS)
        self.shot = self._combo(prompts.SHOT_PRESETS)
        self.setting = self._combo(prompts.SETTING_PRESETS)
        self.lighting = self._combo(prompts.LIGHTING_PRESETS)
        self.style = self._combo(prompts.STYLE_PRESETS)
        self.custom = QLineEdit()
        self.custom.setPlaceholderText("custom (any language)")
        self.custom.textChanged.connect(self._update_preview)

        lay.addWidget(self._group("Main", [("Age", self.age), ("Gender", self.gender),
                                           ("Pose", self.pose), ("Expression", self.expr)]))
        lay.addWidget(self._group("Auxiliary", [("Body", self.body), ("Skin tone", self.skin),
                                                ("Hair", self.hair), ("Shot", self.shot),
                                                ("Setting", self.setting), ("Lighting", self.lighting)]))
        lay.addWidget(self._group("Extra", [("Style / vibe", self.style), ("Custom", self.custom)]))

        self._rnd_combos = [self.age, self.gender, self.pose, self.expr,
                            self.body, self.skin, self.hair, self.shot, self.setting, self.lighting]
        self._all_combos = self._rnd_combos + [self.style]

        self.preview_toggle = QPushButton("▸  Prompt preview")
        self.preview_toggle.setProperty("flat", True)
        self.preview_toggle.setCheckable(True)
        self.preview_toggle.setCursor(Qt.PointingHandCursor)
        self.preview_toggle.toggled.connect(self._toggle_preview)
        lay.addWidget(self.preview_toggle)
        self.prompt_box = QPlainTextEdit()
        self.prompt_box.setReadOnly(True)
        self.prompt_box.setFixedHeight(80)
        self.prompt_box.setVisible(False)
        lay.addWidget(self.prompt_box)

        lay.addStretch(1)
        ctl = QHBoxLayout()
        ctl.addWidget(ModelSelector("G1"), 1)
        self.realism = QPushButton("Realism: on")
        self.realism.setCheckable(True)
        self.realism.setChecked(True)
        self.realism.setCursor(Qt.PointingHandCursor)
        self.realism.toggled.connect(lambda on: self.realism.setText(f"Realism: {'on' if on else 'off'}"))
        ctl.addWidget(self.realism)
        lay.addLayout(ctl)

        actions = QHBoxLayout()
        self.gen_btn = QPushButton("Generate")
        self.gen_btn.setProperty("accent", True)
        self.gen_btn.setCursor(Qt.PointingHandCursor)
        self.gen_btn.clicked.connect(self._generate)
        save = QPushButton("Save")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)
        actions.addWidget(self.gen_btn, 1)
        actions.addWidget(save)
        lay.addLayout(actions)
        return panel

    # ------------------------------------------------------------- builders
    def _h3(self, t):
        lb = QLabel(t); lb.setObjectName("h3"); return lb

    def _combo(self, presets):
        c = QComboBox(); c.setEditable(True); c.addItems(presets); c.setCurrentIndex(0)
        c.currentTextChanged.connect(self._update_preview)
        return c

    def _field(self, label, widget):
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(3)
        lb = QLabel(label); lb.setObjectName("formLabel")
        v.addWidget(lb); v.addWidget(widget)
        return w

    def _group(self, title, specs):
        box = QWidget(); v = QVBoxLayout(box); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(5)
        v.addWidget(self._h3(title))
        grid = QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(6)
        fields = [self._field(lb, w) for lb, w in specs]
        for i, fw in enumerate(fields):
            grid.addWidget(fw, i // 2, i % 2)
        self._grids.append((grid, fields))
        v.addLayout(grid)
        return box

    # ------------------------------------------------------------- responsive columns
    def _on_params_resize(self, w):
        cols = 3 if w >= 470 else 2 if w >= 300 else 1
        if cols != self._cols:
            self._cols = cols
            for grid, fields in self._grids:
                for fw in fields:
                    grid.removeWidget(fw)
                for i, fw in enumerate(fields):
                    grid.addWidget(fw, i // cols, i % cols)

    # ------------------------------------------------------------- data
    def _params(self) -> dict:
        return {"age": self.age.currentText(), "gender": self.gender.currentText(),
                "body": self.body.currentText(), "skin": self.skin.currentText(),
                "hair": self.hair.currentText(), "expression": self.expr.currentText(),
                "pose": self.pose.currentText(), "shot": self.shot.currentText(),
                "setting": self.setting.currentText(), "lighting": self.lighting.currentText(),
                "style": self.style.currentText(), "custom": self.custom.text().strip()}

    def _realism_on(self):
        return self.realism.isChecked()

    def _update_preview(self):
        self.prompt_box.setPlainText(prompts.model_prompt(self._params()) + "  + realism markers")

    def _toggle_preview(self, on):
        self.prompt_box.setVisible(on)
        self.preview_toggle.setText(("▾  " if on else "▸  ") + "Prompt preview")

    def _rnd(self):
        for c in self._rnd_combos:
            if c.count():
                c.setCurrentIndex(random.randrange(c.count()))
        self._update_preview()

    def _rst(self):
        for c in self._all_combos:
            c.setCurrentIndex(0)
        self.custom.clear()
        self._update_preview()

    def _show(self, path):
        if path and Path(path).exists():
            self.preview.setPixmap(QPixmap(path).scaled(
                self.preview.width(), self.preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview.clear()
            self.preview.setText("No model yet\nset parameters, then generate")

    # ------------------------------------------------------------- actions
    def _generate(self):
        self.status.setText("Generating model…")
        self.gen_btn.setEnabled(False)

        def ok(path):
            self.gen_btn.setEnabled(True)
            self._cur["image"] = path
            self._show(path)
            self.status.setText("Done.")

        def err(msg):
            self.gen_btn.setEnabled(True)
            self.status.setText(msg)

        run_async(personas.generate_model, ok, err, self._params(), self._realism_on())

    def _save(self):
        name = self.name.text().strip()
        if not name:
            self.status.setText("Enter a name before saving.")
            return
        if not self._cur["image"]:
            self.status.setText("Generate a model first.")
            return
        traits = self._params()
        img = self._cur["image"]
        if self._cur["id"]:
            personas.update(self._cur["id"], name, None, traits, img, img)
            pid = self._cur["id"]
        else:
            pid = personas.create(name, None, traits, img, img)
            self._cur["id"] = pid
        self.library.reload(select_id=pid)
        self._refresh_count()
        self.status.setText(f"Saved “{name}”.")

    def _new(self):
        self._cur = {"id": None, "image": None}
        self.name.clear()
        self.custom.clear()
        self._show(None)
        self.library.clearSelection()
        self.status.setText("New model. Set parameters and Generate.")

    def _load(self, pid):
        p = personas.get(pid)
        if not p:
            return
        self._cur = {"id": p["id"], "image": p["fullbody_path"]}
        self.name.setText(p.get("name") or "")
        t = p.get("traits") or {}
        for key, w in (("age", self.age), ("gender", self.gender), ("body", self.body),
                       ("skin", self.skin), ("hair", self.hair), ("expression", self.expr),
                       ("pose", self.pose), ("shot", self.shot), ("setting", self.setting),
                       ("lighting", self.lighting), ("style", self.style)):
            if t.get(key):
                w.setCurrentText(t[key])
        self.custom.setText(t.get("custom", ""))
        self._show(p["fullbody_path"])
        self.status.setText(f"Loaded “{p.get('name') or pid}”.")

    def _refresh_count(self):
        self.count_lbl.setText(f"{personas.count()} models")
