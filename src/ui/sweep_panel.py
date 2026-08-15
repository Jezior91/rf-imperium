"""RF Imperium — Sweep Panel"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QDoubleSpinBox,
                               QSpinBox, QGroupBox, QTableWidget,
                               QTableWidgetItem, QProgressBar, QFileDialog)
from PyQt6.QtCore import pyqtSignal
import pyqtgraph as pg
import numpy as np


class SweepPanel(QWidget):
    sig_start = pyqtSignal(float, float, float, int, float)  # start,stop,step,dwell,thresh
    sig_stop = pyqtSignal()
    sig_export = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result_freqs = []
        self._result_powers = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Settings
        grp = QGroupBox("Sweep Settings")
        grp.setStyleSheet("QGroupBox{color:#0cf;font-weight:bold;}")
        g = QGridLayout(grp)

        def mhz_spin(lo, hi, val, step=1.0):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setValue(val)
            s.setSuffix(" MHz"); s.setDecimals(3); s.setSingleStep(step)
            s.setStyleSheet("background:#1a1a2e;color:#fff;")
            return s

        self._spin_start = mhz_spin(0.001, 5999, 430.0)
        self._spin_stop = mhz_spin(0.001, 6000, 440.0)
        self._spin_step = mhz_spin(0.001, 100, 0.25, 0.1)
        self._spin_dwell = QSpinBox()
        self._spin_dwell.setRange(10,5000); self._spin_dwell.setValue(100)
        self._spin_dwell.setSuffix(" ms"); self._spin_dwell.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_thresh = QDoubleSpinBox()
        self._spin_thresh.setRange(-120,0); self._spin_thresh.setValue(-70)
        self._spin_thresh.setSuffix(" dBm"); self._spin_thresh.setStyleSheet("background:#1a1a2e;color:#fff;")

        g.addWidget(QLabel("Start:"),0,0); g.addWidget(self._spin_start,0,1)
        g.addWidget(QLabel("Stop:"),1,0); g.addWidget(self._spin_stop,1,1)
        g.addWidget(QLabel("Step:"),2,0); g.addWidget(self._spin_step,2,1)
        g.addWidget(QLabel("Dwell:"),3,0); g.addWidget(self._spin_dwell,3,1)
        g.addWidget(QLabel("Threshold:"),4,0); g.addWidget(self._spin_thresh,4,1)
        layout.addWidget(grp)

        # Quick ranges
        ranges = [("ISM 433\n430-435",430,435,0.05),("ISM 868\n863-870",863,870,0.05),
                  ("VHF\n136-175",136,175,0.1),("UHF\n400-470",400,470,0.1),
                  ("2.4G\n2400-2500",2400,2500,0.5),("WiFi 5G\n5150-5850",5150,5850,1.0),
                  ("Full 0-6G",0.001,6000,10.0)]
        qr = QHBoxLayout()
        for label,s,e,st in ranges:
            btn = QPushButton(label)
            btn.setFixedHeight(36); btn.setFixedWidth(70)
            btn.setStyleSheet("background:#0a0a2e;color:#0cf;border:1px solid #333;font-size:9px;")
            sv,ev,stv = s,e,st
            btn.clicked.connect(lambda _,sv=sv,ev=ev,stv=stv: self._set_range(sv,ev,stv))
            qr.addWidget(btn)
        layout.addLayout(qr)

        # Progress
        self._progress = QProgressBar()
        self._progress.setStyleSheet("QProgressBar{background:#111;border:1px solid #333;color:#fff;}"
                                      "QProgressBar::chunk{background:#0088ff;}")
        self._progress.setValue(0)
        self._lbl_status = QLabel("Gotowy")
        self._lbl_status.setStyleSheet("color:#888;font-size:10px;")
        layout.addWidget(self._progress)
        layout.addWidget(self._lbl_status)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("▶ START SWEEP")
        self._btn_start.setStyleSheet("background:#003300;color:#0f0;border:2px solid #0a0;font-weight:bold;font-size:12px;padding:4px;")
        self._btn_start.clicked.connect(self._start)
        self._btn_stop = QPushButton("■ STOP")
        self._btn_stop.setStyleSheet("background:#330000;color:#f00;border:2px solid #a00;font-weight:bold;font-size:12px;padding:4px;")
        self._btn_stop.clicked.connect(self.sig_stop.emit)
        self._btn_export = QPushButton("Export CSV")
        self._btn_export.setStyleSheet("background:#0a0a2e;color:#88f;border:1px solid #44f;font-size:10px;")
        self._btn_export.clicked.connect(self._export)
        for b in [self._btn_start,self._btn_stop,self._btn_export]:
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        # Sweep plot
        self._plot = pg.PlotWidget(background="#050510")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel("left","Power (dBm)"); self._plot.setLabel("bottom","Frequency (MHz)")
        self._plot.setYRange(-120,0)
        self._curve = self._plot.plot([], [], pen=pg.mkPen("#00aaff",width=1.5))
        self._scatter = pg.ScatterPlotItem(size=8, pen=pg.mkPen("#ff4444"), brush=pg.mkBrush("#ff4444"))
        self._plot.addItem(self._scatter)
        layout.addWidget(self._plot)

        # Peaks table
        self._peaks_table = QTableWidget(0, 3)
        self._peaks_table.setHorizontalHeaderLabels(["Freq (MHz)","Power (dBm)","Band"])
        self._peaks_table.setMaximumHeight(120)
        self._peaks_table.setStyleSheet("QTableWidget{background:#0a0a14;color:#ddd;font-size:10px;}"
                                         "QHeaderView::section{background:#1a1a2e;color:#0cf;}")
        self._peaks_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._peaks_table)

    def _set_range(self, s, e, st):
        self._spin_start.setValue(s); self._spin_stop.setValue(e); self._spin_step.setValue(st)

    def _start(self):
        self._result_freqs=[]; self._result_powers=[]
        self._curve.setData([],[])
        self._peaks_table.setRowCount(0)
        self._progress.setValue(0)
        self.sig_start.emit(
            self._spin_start.value()*1e6, self._spin_stop.value()*1e6,
            self._spin_step.value()*1e6, self._spin_dwell.value(),
            self._spin_thresh.value())

    def _export(self):
        path,_ = QFileDialog.getSaveFileName(self,"Export CSV","sweep_result.csv","CSV (*.csv)")
        if path: self.sig_export.emit(path)

    def update_progress(self, done, total, freq_hz):
        pct = int(100*done/total) if total>0 else 0
        self._progress.setValue(pct)
        self._lbl_status.setText(f"{done}/{total} — {freq_hz/1e6:.3f} MHz")

    def update_point(self, freq_hz, power_dbm):
        self._result_freqs.append(freq_hz/1e6)
        self._result_powers.append(power_dbm)
        self._curve.setData(self._result_freqs, self._result_powers)

    def add_peak(self, freq_hz, power_dbm):
        r = self._peaks_table.rowCount()
        self._peaks_table.insertRow(r)
        mhz = freq_hz/1e6
        band = self._band_name(mhz)
        for c,v in enumerate([f"{mhz:.4f}",f"{power_dbm:.1f}",band]):
            it = QTableWidgetItem(v)
            self._peaks_table.setItem(r,c,it)
        # Update scatter
        x = [f/1e6 for f,p in zip(self._result_freqs,self._result_powers) if p>self._spin_thresh.value()]
        y_vals = [p for p in self._result_powers if p>self._spin_thresh.value()]
        if x: self._scatter.setData(x=x,y=y_vals)

    def sweep_done(self):
        self._progress.setValue(100)
        self._lbl_status.setText(f"Sweep ukończony — {len(self._result_freqs)} punktów")

    def _band_name(self, mhz):
        if mhz<30: return "HF"
        elif mhz<300: return "VHF"
        elif mhz<1000: return "UHF"
        elif mhz<3000: return "L/S Band"
        return "C/X Band"
