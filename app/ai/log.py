"""Central AI call log. EVERY request to any neural net (foreground or background)
goes through here. Entries are kept in memory (never auto-dropped) and persisted to
data/ai_log.jsonl so they survive restarts. A manual 'delete oldest 30' is the only
removal. Thread-safe: AI calls run on worker threads, the UI lives on the main thread.
"""
from __future__ import annotations

import json
import threading
import time

from PySide6.QtCore import QObject, Signal

from .. import config


class LogEntry:
    __slots__ = ("id", "provider", "op", "model", "kinds", "status", "ts",
                 "request", "response", "result")

    def __init__(self, id, provider, op, model, kinds, request):
        self.id = id
        self.provider = provider
        self.op = op
        self.model = model
        self.kinds = kinds
        self.status = "pending"
        self.ts = time.time()
        self.request = request
        self.response = None
        self.result = None

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}

    @classmethod
    def from_dict(cls, d: dict) -> "LogEntry":
        e = cls(d["id"], d["provider"], d["op"], d["model"], d.get("kinds", []), d.get("request"))
        e.status = d.get("status", "ok")
        e.ts = d.get("ts", 0)
        e.response = d.get("response")
        e.result = d.get("result")
        return e


class _Store(QObject):
    added = Signal(object)     # new pending entry
    updated = Signal(object)   # entry finished/errored
    changed = Signal()         # bulk change (delete)

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._items: list[LogEntry] = []
        self._seq = 0
        self._path = config.DATA_DIR / "ai_log.jsonl"
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = LogEntry.from_dict(json.loads(line))
                    self._items.append(e)
                    self._seq = max(self._seq, e.id)
        except Exception:
            pass

    def _append(self, e: LogEntry) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def _rewrite(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                for e in self._items:
                    if e.status != "pending":
                        f.write(json.dumps(e.to_dict(), ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    # ---- write API (called from worker threads) ----
    def start(self, provider, op, model, kinds, request) -> LogEntry:
        with self._lock:
            self._seq += 1
            e = LogEntry(self._seq, provider, op, model, list(kinds), request)
            self._items.append(e)
        self.added.emit(e)
        return e

    def finish(self, e: LogEntry, response=None, result=None) -> None:
        e.status = "ok"
        e.response = response
        e.result = result
        self._append(e)
        self.updated.emit(e)

    def error(self, e: LogEntry, message: str) -> None:
        e.status = "error"
        e.result = message
        self._append(e)
        self.updated.emit(e)

    # ---- read API (main thread) ----
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    def newest_first(self) -> list[LogEntry]:
        with self._lock:
            return list(reversed(self._items))

    def delete_oldest(self, n: int = 30) -> None:
        with self._lock:
            del self._items[:n]
            self._rewrite()
        self.changed.emit()


STORE = _Store()
