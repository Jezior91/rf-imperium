"""RF Imperium — Spoofer / TX Panel"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QLineEdit, QSpinBox,
                               QDoubleSpinBox, QComboBox, QGroupBox,
                               QTextEdit, QCheckBox)
from PyQt6.QtCore import pyqtSignal


class SpooferPanel(QWidget):
    sig_send_ook = pyqtSignal(str, float, float)    # bits, freq_hz, sym_rate
    sig_send_fsk = pyqtSignal(str, float, float, float, float)  # bits,freq,fmark,fspace,symrate
    sig_replay = pyqtSignal(int, float)             # repeat, delay
    sig_bruteforce = pyqtSignal(float, int, float)  # freq, bit_len, sym_rate
    sig_stop = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Mode selector
        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["OOK/ASK TX","FSK TX","Replay","Bruteforce OOK"])
        self._combo_mode.setStyleSheet("background:#1a1a2e;color:#fff;font-size:11px;")
        self._combo_mode.currentIndexChanged.connect(self._update_mode)
        layout.addWidget(self._combo_mode)

        # OOK group
        self._grp_ook = QGroupBox("OOK/ASK Transmit")
        self._grp_ook.setStyleSheet("QGroupBox{color:#fa0;font-weight:bold;}")
        go = QGridLayout(self._grp_ook)
        self._edit_bits = QLineEdit("10101010111010101010101011100000")
        self._edit_bits.setStyleSheet("background:#0a0a1e;color:#0ff;font-family:monospace;")
        self._edit_bits.setPlaceholderText("Bity OOK (0/1)")
        self._spin_ook_freq = QDoubleSpinBox()
        self._spin_ook_freq.setRange(1, 6000); self._spin_ook_freq.setValue(433.92)
        self._spin_ook_freq.setSuffix(" MHz"); self._spin_ook_freq.setDecimals(3)
        self._spin_ook_freq.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_ook_sr = QDoubleSpinBox()
        self._spin_ook_sr.setRange(10, 100000); self._spin_ook_sr.setValue(1000)
        self._spin_ook_sr.setSuffix(" bps"); self._spin_ook_sr.setDecimals(0)
        self._spin_ook_sr.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_ook_rep = QSpinBox()
        self._spin_ook_rep.setRange(1,100); self._spin_ook_rep.setValue(3)
        self._spin_ook_rep.setSuffix("x repeat")
        self._spin_ook_rep.setStyleSheet("background:#1a1a2e;color:#fff;")
        go.addWidget(QLabel("Bity:"), 0, 0); go.addWidget(self._edit_bits, 0, 1, 1, 2)
        go.addWidget(QLabel("Freq:"), 1, 0); go.addWidget(self._spin_ook_freq, 1, 1)
        go.addWidget(QLabel("Sym rate:"), 2, 0); go.addWidget(self._spin_ook_sr, 2, 1)
        go.addWidget(QLabel("Powtórzeń:"), 3, 0); go.addWidget(self._spin_ook_rep, 3, 1)
        layout.addWidget(self._grp_ook)

        # FSK group
        self._grp_fsk = QGroupBox("FSK Transmit")
        self._grp_fsk.setStyleSheet("QGroupBox{color:#fa0;font-weight:bold;}")
        gf = QGridLayout(self._grp_fsk)
        self._edit_fsk_bits = QLineEdit("10101010110000001111")
        self._edit_fsk_bits.setStyleSheet("background:#0a0a1e;color:#0ff;font-family:monospace;")
        self._spin_fsk_freq = QDoubleSpinBox()
        self._spin_fsk_freq.setRange(1,6000); self._spin_fsk_freq.setValue(433.92)
        self._spin_fsk_freq.setSuffix(" MHz"); self._spin_fsk_freq.setDecimals(3)
        self._spin_fsk_freq.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_fmark = QDoubleSpinBox()
        self._spin_fmark.setRange(100,100000); self._spin_fmark.setValue(1200)
        self._spin_fmark.setSuffix(" Hz"); self._spin_fmark.setDecimals(0)
        self._spin_fmark.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_fspace = QDoubleSpinBox()
        self._spin_fspace.setRange(100,100000); self._spin_fspace.setValue(2200)
        self._spin_fspace.setSuffix(" Hz"); self._spin_fspace.setDecimals(0)
        self._spin_fspace.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_fsk_symrate = QDoubleSpinBox()
        self._spin_fsk_symrate.setRange(10,100000); self._spin_fsk_symrate.setValue(1200)
        self._spin_fsk_symrate.setSuffix(" bps"); self._spin_fsk_symrate.setDecimals(0)
        self._spin_fsk_symrate.setStyleSheet("background:#1a1a2e;color:#fff;")
        gf.addWidget(QLabel("Bity:"),0,0); gf.addWidget(self._edit_fsk_bits,0,1,1,2)
        gf.addWidget(QLabel("Freq:"),1,0); gf.addWidget(self._spin_fsk_freq,1,1)
        gf.addWidget(QLabel("f_mark:"),2,0); gf.addWidget(self._spin_fmark,2,1)
        gf.addWidget(QLabel("f_space:"),3,0); gf.addWidget(self._spin_fspace,3,1)
        gf.addWidget(QLabel("Sym rate:"),4,0); gf.addWidget(self._spin_fsk_symrate,4,1)
        self._grp_fsk.hide()
        layout.addWidget(self._grp_fsk)

        # Replay group
        self._grp_replay = QGroupBox("Replay (ostatni RX)")
        self._grp_replay.setStyleSheet("QGroupBox{color:#fa0;font-weight:bold;}")
        gr = QGridLayout(self._grp_replay)
        self._spin_rep_count = QSpinBox()
        self._spin_rep_count.setRange(1,50); self._spin_rep_count.setValue(3)
        self._spin_rep_count.setSuffix("x")
        self._spin_rep_count.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_rep_delay = QDoubleSpinBox()
        self._spin_rep_delay.setRange(0.05,5.0); self._spin_rep_delay.setValue(0.2)
        self._spin_rep_delay.setSuffix(" s delay"); self._spin_rep_delay.setDecimals(2)
        self._spin_rep_delay.setStyleSheet("background:#1a1a2e;color:#fff;")
        gr.addWidget(QLabel("Powtórzeń:"),0,0); gr.addWidget(self._spin_rep_count,0,1)
        gr.addWidget(QLabel("Opóźnienie:"),1,0); gr.addWidget(self._spin_rep_delay,1,1)
        self._grp_replay.hide()
        layout.addWidget(self._grp_replay)

        # Bruteforce group
        self._grp_bf = QGroupBox("Bruteforce OOK")
        self._grp_bf.setStyleSheet("QGroupBox{color:#f44;font-weight:bold;}")
        gb = QGridLayout(self._grp_bf)
        self._spin_bf_freq = QDoubleSpinBox()
        self._spin_bf_freq.setRange(1,6000); self._spin_bf_freq.setValue(433.92)
        self._spin_bf_freq.setSuffix(" MHz"); self._spin_bf_freq.setDecimals(3)
        self._spin_bf_freq.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_bf_bits = QSpinBox()
        self._spin_bf_bits.setRange(8,24); self._spin_bf_bits.setValue(12)
        self._spin_bf_bits.setSuffix(" bit")
        self._spin_bf_bits.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_bf_sr = QDoubleSpinBox()
        self._spin_bf_sr.setRange(10,100000); self._spin_bf_sr.setValue(1000)
        self._spin_bf_sr.setSuffix(" bps"); self._spin_bf_sr.setDecimals(0)
        self._spin_bf_sr.setStyleSheet("background:#1a1a2e;color:#fff;")
        gb.addWidget(QLabel("Freq:"),0,0); gb.addWidget(self._spin_bf_freq,0,1)
        gb.addWidget(QLabel("Długość:"),1,0); gb.addWidget(self._spin_bf_bits,1,1)
        gb.addWidget(QLabel("Sym rate:"),2,0); gb.addWidget(self._spin_bf_sr,2,1)
        self._grp_bf.hide()
        layout.addWidget(self._grp_bf)

        # TX Safety
        self._chk_safety = QCheckBox("TX ENABLED (uwaga: nadawanie RF!)")
        self._chk_safety.setStyleSheet("color:#f44;font-weight:bold;")
        layout.addWidget(self._chk_safety)

        # Action buttons
        btn_row = QHBoxLayout()
        self._btn_send = QPushButton("▶ SEND")
        self._btn_send.setStyleSheet(
            "background:#003300;color:#0f0;border:2px solid #0a0;font-weight:bold;font-size:13px;padding:4px;")
        self._btn_send.clicked.connect(self._send)
        self._btn_stop = QPushButton("■ STOP")
        self._btn_stop.setStyleSheet(
            "background:#330000;color:#f00;border:2px solid #a00;font-weight:bold;font-size:13px;padding:4px;")
        self._btn_stop.clicked.connect(self.sig_stop.emit)
        btn_row.addWidget(self._btn_send); btn_row.addWidget(self._btn_stop)
        layout.addLayout(btn_row)

        # Log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(80)
        self._log.setStyleSheet("background:#060606;color:#888;font-size:9px;font-family:monospace;")
        layout.addWidget(self._log)
        layout.addStretch()

    def _update_mode(self, idx):
        self._grp_ook.setVisible(idx==0)
        self._grp_fsk.setVisible(idx==1)
        self._grp_replay.setVisible(idx==2)
        self._grp_bf.setVisible(idx==3)

    def _send(self):
        if not self._chk_safety.isChecked():
            self.log("TX DISABLED — zaznacz 'TX ENABLED' aby nadawać")
            return
        idx = self._combo_mode.currentIndex()
        if idx==0:
            self.sig_send_ook.emit(
                self._edit_bits.text(),
                self._spin_ook_freq.value()*1e6,
                self._spin_ook_sr.value())
        elif idx==1:
            self.sig_send_fsk.emit(
                self._edit_fsk_bits.text(),
                self._spin_fsk_freq.value()*1e6,
                self._spin_fmark.value(),
                self._spin_fspace.value(),
                self._spin_fsk_symrate.value())
        elif idx==2:
            self.sig_replay.emit(
                self._spin_rep_count.value(),
                self._spin_rep_delay.value())
        elif idx==3:
            self.sig_bruteforce.emit(
                self._spin_bf_freq.value()*1e6,
                self._spin_bf_bits.value(),
                self._spin_bf_sr.value())

    def log(self, msg: str):
        self._log.append(msg)

    def is_tx_enabled(self): return self._chk_safety.isChecked()

    def load_bits(self, bits: str, freq_mhz: float):
        self._edit_bits.setText(bits)
        self._spin_ook_freq.setValue(freq_mhz)
