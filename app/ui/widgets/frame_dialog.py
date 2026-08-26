"""Frame-pick popup: scrub a downloaded reel and save the chosen still (cv2-based)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
)

from ... import collect, config, db


class VideoReader:
    def __init__(self, path):
        import cv2
        self.cv2 = cv2
        self.cap = cv2.VideoCapture(str(path))
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    def frame(self, idx) -> QImage | None:
        cv2 = self.cv2
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(idx, self.count - 1)))
        ok, fr = self.cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()

    def release(self):
        try:
            self.cap.release()
        except Exception:
            pass


class FrameDialog(QDialog):
    def __init__(self, video_path, link_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick a frame from the reel")
        self.resize(420, 660)
        self.link_id = link_id
        self.saved_path = None
        self._cur = None
        try:
            self.reader = VideoReader(video_path)
        except Exception:
            self.reader = None

        lay = QVBoxLayout(self)
        self.preview = QLabel("…")
        self.preview.setObjectName("imgPanel")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(500)
        lay.addWidget(self.preview, 1)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setToolTip("Scrub the reel")
        if self.reader and self.reader.count > 0:
            self.slider.setRange(0, self.reader.count - 1)
            self.slider.valueChanged.connect(self._show)
            self._show(0)
        else:
            self.preview.setText("Could not read the video.")
            self.slider.setEnabled(False)
        lay.addWidget(self.slider)

        foot = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save frame")
        save.setProperty("accent", True)
        save.clicked.connect(self._save)
        foot.addStretch(1)
        foot.addWidget(cancel)
        foot.addWidget(save)
        lay.addLayout(foot)

    def _show(self, idx):
        if not self.reader:
            return
        img = self.reader.frame(idx)
        if img is None:
            return
        self._cur = img
        self.preview.setPixmap(QPixmap.fromImage(img).scaled(
            self.preview.width(), self.preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _save(self):
        if self._cur is None:
            self.reject()
            return
        config.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        dest = config.FRAMES_DIR / f"frame_{int(db.now() * 1000)}.png"
        self._cur.save(str(dest))
        collect.save_frame(self.link_id, str(dest))
        self.saved_path = str(dest)
        self.accept()

    def closeEvent(self, e):
        if self.reader:
            self.reader.release()
        super().closeEvent(e)
