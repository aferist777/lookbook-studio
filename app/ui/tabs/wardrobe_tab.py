"""Wardrobe tab — the hub. Two views (Search / Wardrobe) behind a segmented switch.

Search: keyword query via the AliExpress Affiliate API (source dropdown = engine),
results as starrable product cards. Wardrobe: the saved items. Paginated so the page
never scrolls vertically (per the app-wide no-scroll rule, for now).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from ... import wardrobe
from ...sources.base import ENGINES, get_source
from ...workers import run_async
from ..widgets.product_card import ProductCard


class WardrobeTab(QWidget):
    PAGE = 12
    COLS = 6

    def __init__(self):
        super().__init__()
        self._search_page = 1
        self._ward_page = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 16)
        root.setSpacing(14)

        root.addWidget(self._build_segbar(), 0, Qt.AlignLeft)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_search_page())
        self.stack.addWidget(self._build_wardrobe_page())
        root.addWidget(self.stack, 1)

        self._refresh_counts()

    # ------------------------------------------------------------------ segbar
    def _build_segbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("segbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self._seg = QButtonGroup(self)
        for i, text in enumerate(("Search", "Wardrobe")):
            b = QPushButton(text)
            b.setProperty("seg", True)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            self._seg.addButton(b, i)
            lay.addWidget(b)
        self._seg.idClicked.connect(self._switch_view)
        return bar

    def _switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 1:
            self._load_wardrobe()

    # ------------------------------------------------------------------ search
    def _build_search_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        controls = QHBoxLayout()
        controls.setSpacing(9)
        self.engine = QComboBox()
        self.engine.setToolTip("Search engine / source")
        self.engine.setFixedWidth(190)
        model = self.engine.model()
        for eid, label, enabled in ENGINES:
            self.engine.addItem(label, eid)
            if not enabled:
                item = model.item(self.engine.count() - 1)
                if item is not None:
                    item.setEnabled(False)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products, e.g. oversize hoodie men")
        self.search_input.setToolTip("Keywords for the AliExpress Affiliate API (any language)")
        self.search_input.returnPressed.connect(lambda: self._do_search(reset_page=True))

        self.search_btn = QPushButton("Search")
        self.search_btn.setProperty("accent", True)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setToolTip("Run the search")
        self.search_btn.clicked.connect(lambda: self._do_search(reset_page=True))

        controls.addWidget(self.engine)
        controls.addWidget(self.search_input, 1)
        controls.addWidget(self.search_btn)
        lay.addLayout(controls)

        self.status = QLabel("Type keywords and press Search.")
        self.status.setObjectName("status")
        lay.addWidget(self.status)

        self.search_grid_host, self.search_grid = self._grid_host()
        lay.addWidget(self.search_grid_host, 1)

        lay.addLayout(self._pager("search"))
        return page

    def _do_search(self, reset_page: bool = True) -> None:
        kw = self.search_input.text().strip()
        if not kw:
            return
        if reset_page:
            self._search_page = 1
        engine = self.engine.currentData()
        self.status.setText(f"Searching “{kw}”…")
        self.search_btn.setEnabled(False)
        page = self._search_page

        def task():
            return get_source(engine).search(kw, page=page, page_size=self.PAGE)

        run_async(task, self._on_results, self._on_search_error)

    def _on_results(self, results) -> None:
        self.search_btn.setEnabled(True)
        self._clear_grid(self.search_grid)
        if not results:
            self.status.setText("No results.")
            return
        self.status.setText(f"{len(results)} results · page {self._search_page}")
        for i, r in enumerate(results):
            card = r.to_card()
            w = ProductCard(card, starred=wardrobe.is_saved(card.get("product_id"), card.get("source", "aliexpress")))
            w.starToggled.connect(self._on_search_star)
            self.search_grid.addWidget(w, i // self.COLS, i % self.COLS)
        self.search_page_lbl.setText(f"Page {self._search_page}")

    def _on_search_error(self, msg: str) -> None:
        self.search_btn.setEnabled(True)
        self.status.setText(msg)

    def _on_search_star(self, card: dict, checked: bool) -> None:
        if checked:
            run_async(wardrobe.save_result, lambda _i: self._refresh_counts(), self._noop, card)
        else:
            run_async(wardrobe.delete_by_product, lambda _r: self._refresh_counts(), self._noop,
                      card.get("product_id"), card.get("source", "aliexpress"))

    # ------------------------------------------------------------------ wardrobe
    def _build_wardrobe_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        header = QHBoxLayout()
        self.ward_count = QLabel("0 items")
        self.ward_count.setObjectName("sectionCount")
        refresh = QPushButton("Refresh")
        refresh.setProperty("flat", True)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self._load_wardrobe)
        header.addWidget(self.ward_count)
        header.addStretch(1)
        header.addWidget(refresh)
        lay.addLayout(header)

        self.ward_grid_host, self.ward_grid = self._grid_host()
        lay.addWidget(self.ward_grid_host, 1)

        lay.addLayout(self._pager("ward"))
        return page

    def _load_wardrobe(self) -> None:
        total = wardrobe.count_items()
        pages = max(1, (total + self.PAGE - 1) // self.PAGE)
        self._ward_page = min(self._ward_page, pages - 1)
        items = wardrobe.list_items(self.PAGE, self._ward_page * self.PAGE)
        self._clear_grid(self.ward_grid)
        for i, card in enumerate(items):
            w = ProductCard(card, starred=True)
            w.starToggled.connect(self._on_ward_star)
            self.ward_grid.addWidget(w, i // self.COLS, i % self.COLS)
        self.ward_count.setText(f"{total} items")
        self.ward_page_lbl.setText(f"Page {self._ward_page + 1} / {pages}")

    def _on_ward_star(self, card: dict, checked: bool) -> None:
        if not checked and card.get("id") is not None:
            wardrobe.delete_item(card["id"])
            self._load_wardrobe()
            self._refresh_counts()

    # ------------------------------------------------------------------ helpers
    def _grid_host(self):
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        return host, grid

    def _pager(self, which: str) -> QHBoxLayout:
        prev = QPushButton("◀  Prev")
        nxt = QPushButton("Next  ▶")
        for b in (prev, nxt):
            b.setProperty("flat", True)
            b.setCursor(Qt.PointingHandCursor)
        lbl = QLabel("Page 1")
        lbl.setObjectName("status")
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(prev)
        row.addWidget(lbl)
        row.addWidget(nxt)
        row.addStretch(1)
        if which == "search":
            self.search_page_lbl = lbl
            prev.clicked.connect(self._search_prev)
            nxt.clicked.connect(self._search_next)
        else:
            self.ward_page_lbl = lbl
            prev.clicked.connect(self._ward_prev)
            nxt.clicked.connect(self._ward_next)
        return row

    def _search_prev(self) -> None:
        if self._search_page > 1:
            self._search_page -= 1
            self._do_search(reset_page=False)

    def _search_next(self) -> None:
        self._search_page += 1
        self._do_search(reset_page=False)

    def _ward_prev(self) -> None:
        if self._ward_page > 0:
            self._ward_page -= 1
            self._load_wardrobe()

    def _ward_next(self) -> None:
        self._ward_page += 1
        self._load_wardrobe()

    def _refresh_counts(self) -> None:
        n = wardrobe.count_items()
        btn = self._seg.button(1)
        if btn:
            btn.setText(f"Wardrobe ({n})")

    @staticmethod
    def _noop(*_a) -> None:
        pass

    @staticmethod
    def _clear_grid(grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
