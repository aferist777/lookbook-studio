"""Shared types + engine registry for product search sources."""
from __future__ import annotations

from dataclasses import asdict, dataclass


class SourceError(RuntimeError):
    pass


@dataclass
class SearchResult:
    title: str
    price: float | None
    currency: str
    rating: float | None      # 0-5
    orders: int | None
    image_url: str | None
    affiliate_url: str | None
    source_url: str | None
    product_id: str
    source: str               # e.g. "aliexpress"

    def to_card(self) -> dict:
        d = asdict(self)
        d["image"] = self.image_url
        return d


# Engine dropdown options: (id, label, enabled)
ENGINES: list[tuple[str, str, bool]] = [
    ("aliexpress_keyword", "AliExpress · keyword", True),
    ("aliexpress_image", "AliExpress · by image", False),
    ("temu", "Temu (later)", False),
]


def get_source(engine_id: str):
    if engine_id == "aliexpress_keyword":
        from .aliexpress import AliExpressKeywordSource
        return AliExpressKeywordSource()
    raise SourceError(f"Engine '{engine_id}' is not available yet.")
