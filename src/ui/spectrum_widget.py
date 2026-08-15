"""RF Imperium — Spectrum Analyzer Widget (PyQtGraph)"""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class SpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fft_size = 1024
        self._sample_rate = 2e6
        self._center_freq = 433.92e6
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        tb = QHBoxLayout()
        self._lbl_peak = QLabel("Peak: ---")
        self._lbl_peak.setStyleSheet("color:#0ff;font-size:11px;")
        for label, fn in [("Peak Reset", self._reset_peak),
                           ("Avg Reset", self._reset_avg)]:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.setStyleSheet("background:#333;color:#ccc;border:1px solid #555;font-size:10px;")
            btn.clicked.connect(fn)
            tb.addWidget(btn)
        tb.addWidget(self._lbl_peak)
        tb.addStretch()
        layout.addLayout(tb)

        # Spectrum plot
        self._plot = pg.PlotWidget(background="#0a0a12")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel("left", "Power (dBm)")
        self._plot.setLabel("bottom", "Frequency (MHz)")
        self._plot.setYRange(-120, 0)

        x = np.linspace(0, 1, self._fft_size)
        self._curve_fft = self._plot.plot(x, np.full(self._fft_size, -120),
                                           pen=pg.mkPen("#00ff88", width=1.5))
        self._curve_avg = self._plot.plot(x, np.full(self._fft_size, -120),
                                           pen=pg.mkPen("#ff8800", width=1, style=Qt.PenStyle.DashLine))
        self._curve_peak = self._plot.plot(x, np.full(self._fft_size, -120),
                                            pen=pg.mkPen("#ff2222", width=1))

        # Frequency lines
        self._vline = pg.InfiniteLine(angle=90, movable=False,
                                       pen=pg.mkPen("#ffff00", width=1))
        self._plot.addItem(self._vline)
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_move)

        layout.addWidget(self._plot)
        self._freqs = x
        self._peak_data = np.full(self._fft_size, -120.0)
        self._avg_data = np.full(self._fft_size, -120.0)

    def update_data(self, fft_data: dict):
        freqs_hz = fft_data.get("freqs")
        power = fft_data.get("fft")
        avg = fft_data.get("avg")
        peak = fft_data.get("peak")
        if freqs_hz is None or power is None:
            return

        freqs_mhz = freqs_hz / 1e6
        self._freqs = freqs_mhz
        self._peak_data = peak if peak is not None else power

        self._curve_fft.setData(freqs_mhz, power)
        if avg is not None:
            self._curve_avg.setData(freqs_mhz, avg)
            self._avg_data = avg
        if peak is not None:
            self._curve_peak.setData(freqs_mhz, peak)

        # Update peak label
        if len(power) > 0:
            idx = np.argmax(power)
            self._lbl_peak.setText(
                f"Peak: {freqs_mhz[idx]:.4f} MHz  {power[idx]:.1f} dBm")

        # Update X axis
        if len(freqs_mhz) > 1:
            self._plot.setXRange(freqs_mhz[0], freqs_mhz[-1], padding=0)

    def _on_mouse_move(self, pos):
        if self._plot.sceneBoundingRect().contains(pos):
            mp = self._plot.plotItem.vb.mapSceneToView(pos)
            self._vline.setPos(mp.x())

    def _reset_peak(self):
        self._peak_data[:] = -120.0
        self._curve_peak.setData(self._freqs, self._peak_data)

    def _reset_avg(self):
        self._avg_data[:] = -120.0
        self._curve_avg.setData(self._freqs, self._avg_data)

    def set_freq_range(self, center_hz, sample_rate):
        self._center_freq = center_hz
        self._sample_rate = sample_rate
