"""AliExpress official Affiliate API source (keyword search → affiliate links).

Uses the python-aliexpress-api wrapper. Requires app_key / app_secret / tracking_id
in config.json -> aliexpress. The hot-products endpoint returns products whose
`promotion_link` is already an affiliate link carrying the tracking id.
"""
from __future__ import annotations

from .. import config as cfg
from .base import SearchResult, SourceError


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class AliExpressKeywordSource:
    id = "aliexpress_keyword"
    label = "AliExpress · keyword"

    def _api(self):
        c = cfg.CONFIG.aliexpress
        key, secret, tracking = c.get("app_key"), c.get("app_secret"), c.get("tracking_id")
        if not (key and secret and tracking):
            raise SourceError(
                "Set AliExpress app_key / app_secret / tracking_id in config.json."
            )
        try:
            from aliexpress_api import AliexpressApi, models
        except ImportError as e:
            raise SourceError(
                "Install python-aliexpress-api (pip install python-aliexpress-api)."
            ) from e
        lang = getattr(models.Language, c.get("language", "EN"), models.Language.EN)
        curr = getattr(models.Currency, c.get("currency", "USD"), models.Currency.USD)
        return AliexpressApi(key, secret, lang, curr, tracking)

    def search(self, keywords: str, page: int = 1, page_size: int = 20) -> list[SearchResult]:
        api = self._api()
        resp = api.get_hotproducts(keywords=keywords, page_no=page, page_size=page_size)
        products = getattr(resp, "products", None) or []
        return [self._map(p) for p in products]

    # ---- field mapping (defensive: wrapper field names vary by version) ----
    @staticmethod
    def _rating(p):
        raw = getattr(p, "evaluate_rate", None)  # e.g. "92.0%"
        if not raw:
            return None
        try:
            return round(float(str(raw).strip().rstrip("%")) / 20.0, 1)
        except ValueError:
            return None

    @staticmethod
    def _price(p):
        for attr in ("target_sale_price", "target_app_sale_price", "sale_price"):
            v = getattr(p, attr, None)
            if v:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    def _map(self, p) -> SearchResult:
        c = cfg.CONFIG.aliexpress
        return SearchResult(
            title=getattr(p, "product_title", "") or "",
            price=self._price(p),
            currency=getattr(p, "target_sale_price_currency", "") or c.get("currency", "USD"),
            rating=self._rating(p),
            orders=_to_int(getattr(p, "lastest_volume", None)),
            image_url=getattr(p, "product_main_image_url", None),
            affiliate_url=getattr(p, "promotion_link", None),
            source_url=getattr(p, "product_detail_url", None),
            product_id=str(getattr(p, "product_id", "") or ""),
            source="aliexpress",
        )
