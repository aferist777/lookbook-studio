"""Per-operation model selector. Shows the registry options for an AI call id and
persists the choice between sessions (config.model_choices)."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from ... import config
from ...ai.registry import REGISTRY


class ModelSelector(QComboBox):
    def __init__(self, call_id: str):
        super().__init__()
        self.call_id = call_id
        spec = REGISTRY[call_id]
        for model in spec.options:
            self.addItem(model.split("/")[-1], model)
        current = config.CONFIG.model_choices.get(call_id) or spec.default
        idx = self.findData(current)
        if idx >= 0:
            self.setCurrentIndex(idx)
        self.setToolTip(f"Model for: {spec.note}. Saved between sessions.")
        self.setMinimumWidth(170)
        self.currentIndexChanged.connect(self._save)

    def _save(self) -> None:
        model = self.currentData()
        if model:
            config.CONFIG.set_model_choice(self.call_id, model)
