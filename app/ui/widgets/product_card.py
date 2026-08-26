"""Product card: packshot, title, price, rating, orders, source badge, star toggle."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ...workers import run_async

CARD_W = 188
THUMB_H = 208


def _fetch_bytes(url: str) -> bytes:
    import requests
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.content


def _money(price, currency) -> str:
    if price is None:
        return "—"
    sym = {"USD": "$", "EUR": "€", "RUB": "₽"}.get(currency, "")
    return f"{sym}{price:.2f}" if sym else f"{price:.2f} {currency}".strip()


def _meta(rating, orders) -> str:
    bits = []
    if rating is not None:
        bits.append(f"★ {rating}")
    if orders is not None:
        bits.append(f"{orders:,} orders".replace(",", " "))
    return "  ·  ".join(bits)


class ProductCard(QFrame):
    starToggled = Signal(dict, bool)

    def __init__(self, card: dict, starred: bool = False):
        super().__init__()
        self.card = card
        self.setObjectName("pcard")
        self.setFixedWidth(CARD_W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 12)
        lay.setSpacing(7)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        badge = QLabel((card.get("source") or "").upper() or "—")
        badge.setObjectName("badgeSrc")
        self.star = QPushButton("★")
        self.star.setObjectName("star")
        self.star.setCheckable(True)
        self.star.setChecked(starred)
        self.star.setCursor(Qt.PointingHandCursor)
        self.star.setToolTip("Add this item to the wardrobe / remove it")
        self.star.toggled.connect(lambda c: self.starToggled.emit(self.card, c))
        head.addWidget(badge)
        head.addStretch(1)
        head.addWidget(self.star)
        lay.addLayout(head)

        self.thumb = QLabel("…")
        self.thumb.setObjectName("cardThumb")
        self.thumb.setFixedHeight(THUMB_H)
        self.thumb.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.thumb)

        title = QLabel(card.get("title") or "")
        title.setObjectName("cardTitle")
        title.setWordWrap(True)
        title.setFixedHeight(34)
        title.setTextFormat(Qt.PlainText)
        lay.addWidget(title)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        price = QLabel(_money(card.get("price"), card.get("currency") or ""))
        price.setObjectName("price")
        meta = QLabel(_meta(card.get("rating"), card.get("orders")))
        meta.setObjectName("cardMeta")
        row.addWidget(price)
        row.addStretch(1)
        row.addWidget(meta)
        lay.addLayout(row)

        self.setToolTip(card.get("title") or "")
        self._load_image()

    def _load_image(self) -> None:
        local = self.card.get("packshot_path")
        if local and Path(local).exists():
            pm = QPixmap(local)
            self._apply(pm)
            return
        url = self.card.get("image") or self.card.get("image_url")
        if url:
            run_async(_fetch_bytes, self._on_bytes, self._on_img_error, url)
        else:
            self.thumb.setText("no image")

    def _on_bytes(self, data: bytes) -> None:
        pm = QPixmap()
        pm.loadFromData(QByteArray(data))
        self._apply(pm)

    def _on_img_error(self, _msg: str) -> None:
        self.thumb.setText("no image")

    def _apply(self, pm: QPixmap) -> None:
        if pm.isNull():
            self.thumb.setText("no image")
            return
        self.thumb.setPixmap(
            pm.scaled(CARD_W - 20, THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
