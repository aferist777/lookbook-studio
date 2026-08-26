"""In-app Settings — edit API keys without touching config.json by hand.
Saved immediately and picked up by the next AI call (config is read per-call)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from .. import config


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings · API keys")
        self.setMinimumWidth(540)
        c = config.CONFIG
        ae = c.aliexpress
        tg = c.get("telegram", {}) or {}

        root = QVBoxLayout(self)
        root.setSpacing(10)
        intro = QLabel("Keys are saved to config.json (gitignored) and take effect immediately.")
        intro.setObjectName("subtle")
        root.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(8)
        self.openrouter = self._secret(c.openrouter_api_key)
        self.replicate = self._secret(c.replicate_api_token)
        self.ae_key = QLineEdit(ae.get("app_key", ""))
        self.ae_secret = self._secret(ae.get("app_secret", ""))
        self.ae_track = QLineEdit(ae.get("tracking_id", ""))
        self.ae_lang = QLineEdit(ae.get("language", "EN"))
        self.ae_cur = QLineEdit(ae.get("currency", "USD"))
        self.tg_token = self._secret(tg.get("bot_token", ""))
        self.tg_chan = QLineEdit(tg.get("channel_id", ""))

        form.addRow(self._hdr("OpenRouter  ·  translate + vision"))
        form.addRow("API key", self.openrouter)
        form.addRow(self._hdr("Replicate  ·  image generation + try-on"))
        form.addRow("API token", self.replicate)
        form.addRow(self._hdr("AliExpress Affiliate"))
        form.addRow("App key", self.ae_key)
        form.addRow("App secret", self.ae_secret)
        form.addRow("Tracking id", self.ae_track)
        form.addRow("Language", self.ae_lang)
        form.addRow("Currency", self.ae_cur)
        form.addRow(self._hdr("Telegram  ·  auto-post"))
        form.addRow("Bot token", self.tg_token)
        form.addRow("Channel id", self.tg_chan)
        root.addLayout(form)

        show = QCheckBox("Show keys")
        show.toggled.connect(self._toggle_echo)
        root.addWidget(show)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setProperty("accent", True)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

        self._secrets = [self.openrouter, self.replicate, self.ae_secret, self.tg_token]

    def _secret(self, val) -> QLineEdit:
        e = QLineEdit(val or "")
        e.setEchoMode(QLineEdit.Password)
        return e

    def _hdr(self, text) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("h3")
        return lb

    def _toggle_echo(self, on) -> None:
        for e in self._secrets:
            e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)

    def _save(self) -> None:
        config.CONFIG.set_secrets({
            "openrouter_api_key": self.openrouter.text().strip(),
            "replicate_api_token": self.replicate.text().strip(),
            "aliexpress": {
                "app_key": self.ae_key.text().strip(),
                "app_secret": self.ae_secret.text().strip(),
                "tracking_id": self.ae_track.text().strip(),
                "language": self.ae_lang.text().strip() or "EN",
                "currency": self.ae_cur.text().strip() or "USD",
            },
            "telegram": {
                "bot_token": self.tg_token.text().strip(),
                "channel_id": self.tg_chan.text().strip(),
            },
        })
        self.accept()
