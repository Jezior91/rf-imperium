"""RF Imperium — Waterfall Widget"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class WaterfallWidget(QWidget):
    def __init__(self, fft_size=1024, history=128, parent=None):
        super().__init__(parent)
        self.fft_size = fft_size
        self.history = history
        self._buf = np.full((history, fft_size), -120.0, dtype=np.float32)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._plot = pg.PlotWidget(background="#000010")
        self._img = pg.ImageItem()
        self._plot.addItem(self._img)
        self._plot.setLabel("left", "Time")
        self._plot.setLabel("bottom", "Frequency (MHz)")
        # Colormap
        cm = pg.colormap.get("viridis")
        self._img.setColorMap(cm)
        self._img.setLevels([-120, 0])
        layout.addWidget(self._plot)

    def update_data(self, fft_data: dict):
        wf = fft_data.get("waterfall")
        freqs = fft_data.get("freqs")
        if wf is None: return
        self._buf = wf
        # Update image — transpose so frequency is X axis
        self._img.setImage(self._buf.T, autoLevels=False, levels=[-120, 0])
        if freqs is not None and len(freqs) > 1:
            f0 = freqs[0] / 1e6
            f1 = freqs[-1] / 1e6
            self._img.setRect(pg.QtCore.QRectF(f0, 0, f1 - f0, self.history))
            self._plot.setXRange(f0, f1, padding=0)

    def set_levels(self, low=-120.0, high=0.0):
        self._img.setLevels([low, high])
