"""Tiny QThreadPool helper so network / API calls never block the UI thread."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _Signals(QObject):
    result = Signal(object)
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Signals()

    @Slot()
    def run(self):
        try:
            r = self.fn(*self.args, **self.kwargs)
        except Exception as e:  # surface to the UI, never crash the pool
            self.signals.error.emit(str(e))
        else:
            self.signals.result.emit(r)


def run_async(fn, on_result=None, on_error=None, *args, **kwargs) -> Worker:
    """Run fn(*args, **kwargs) on the global thread pool; deliver result/error on the UI thread."""
    w = Worker(fn, *args, **kwargs)
    if on_result:
        w.signals.result.connect(on_result)
    if on_error:
        w.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(w)
    return w
