"""RF Imperium — Decoder Panel (wyniki dekodowania + AI)"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QPushButton, QLabel,
                               QGroupBox, QTextEdit, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import time


class DecoderPanel(QWidget):
    sig_ai_classify = pyqtSignal(dict)
    sig_replay = pyqtSignal(dict)
    sig_save_db = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Controls
        ctrl = QHBoxLayout()
        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setStyleSheet("background:#2a0a0a;color:#f88;border:1px solid #f44;font-size:10px;")
        self._btn_clear.setFixedHeight(24)
        self._btn_clear.clicked.connect(self._clear)
        self._btn_ai = QPushButton("AI Classify")
        self._btn_ai.setStyleSheet("background:#0a2a0a;color:#0f8;border:1px solid #0f4;font-size:10px;")
        self._btn_ai.setFixedHeight(24)
        self._btn_ai.clicked.connect(self._ai_selected)
        self._btn_replay = QPushButton("Replay TX")
        self._btn_replay.setStyleSheet("background:#2a1a0a;color:#f80;border:1px solid #fa0;font-size:10px;")
        self._btn_replay.setFixedHeight(24)
        self._btn_replay.clicked.connect(self._replay_selected)
        self._btn_save = QPushButton("Save DB")
        self._btn_save.setStyleSheet("background:#0a0a2a;color:#88f;border:1px solid #44f;font-size:10px;")
        self._btn_save.setFixedHeight(24)
        self._btn_save.clicked.connect(self._save_selected)
        self._lbl_count = QLabel("Frames: 0")
        self._lbl_count.setStyleSheet("color:#888;font-size:10px;")
        for w in [self._btn_clear,self._btn_ai,self._btn_replay,self._btn_save,self._lbl_count]:
            ctrl.addWidget(w)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Time","Protocol","Freq (MHz)","Power dBm","Bits/Hex","Decoded"])
        self._table.setStyleSheet(
            "QTableWidget{background:#0a0a14;color:#ddd;gridline-color:#333;font-size:10px;}"
            "QHeaderView::section{background:#1a1a2e;color:#0cf;border:1px solid #333;}")
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        for i,w in enumerate([80,80,90,80,120]):
            self._table.setColumnWidth(i, w)
        layout.addWidget(self._table)

        # Detail view
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(100)
        self._detail.setStyleSheet("background:#06060e;color:#aaa;font-size:9px;font-family:monospace;")
        layout.addWidget(self._detail)

        self._table.itemSelectionChanged.connect(self._show_detail)

    def add_frame(self, frame):
        ts = time.strftime("%H:%M:%S")
        row = self._table.rowCount()
        self._table.insertRow(row)
        items = [ts, frame.protocol,
                 f"{frame.freq_hz/1e6:.4f}",
                 f"{frame.power_dbm:.1f}",
                 frame.hex_data[:20] or frame.bits[:24],
                 frame.decoded[:40]]
        colors = {"EV1527":"#ffaa00","PT2262":"#ffcc00","APRS":"#00ff88",
                  "AIS":"#0088ff","RDS/FM":"#ff44ff","POCSAG":"#ff8800",
                  "OOK":"#00aaff","FSK":"#aaffaa","HOP":"#ff4444"}
        color = QColor(colors.get(frame.protocol, "#cccccc"))
        for c,text in enumerate(items):
            it = QTableWidgetItem(text)
            it.setForeground(color)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row, c, it)
        self._table.scrollToBottom()
        self._frames.append(frame)
        self._lbl_count.setText(f"Frames: {len(self._frames)}")

    def _show_detail(self):
        rows = self._table.selectedItems()
        if not rows: return
        r = self._table.currentRow()
        if r < len(self._frames):
            f = self._frames[r]
            self._detail.setPlainText(
                f"Protocol: {f.protocol}\n"
                f"Freq: {f.freq_hz/1e6:.6f} MHz\n"
                f"Power: {f.power_dbm:.2f} dBm\n"
                f"Bits ({len(f.bits)}): {f.bits}\n"
                f"Hex: {f.hex_data}\n"
                f"Decoded: {f.decoded}\n"
                f"Extra: {f.extra}")

    def _get_selected_frame(self):
        r = self._table.currentRow()
        if 0 <= r < len(self._frames):
            return self._frames[r]
        return None

    def _ai_selected(self):
        f = self._get_selected_frame()
        if f: self.sig_ai_classify.emit(vars(f))

    def _replay_selected(self):
        f = self._get_selected_frame()
        if f: self.sig_replay.emit(vars(f))

    def _save_selected(self):
        f = self._get_selected_frame()
        if f: self.sig_save_db.emit(vars(f))

    def _clear(self):
        self._table.setRowCount(0)
        self._frames.clear()
        self._lbl_count.setText("Frames: 0")
        self._detail.clear()
