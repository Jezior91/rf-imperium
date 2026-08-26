"""RF Imperium v5.0 MAX — ControlPanel (PyQt6)
Panel kontrolny: urządzenie, częstotliwość, wzmocnienia, DSP, nagrywanie IQ.
"""
import json
import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QSlider, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit,
    QGridLayout, QScrollArea, QSizePolicy, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

# Band presets (MHz)
BAND_PRESETS = {
    "AM Radio": 0.720, "FM Radio": 98.0, "Airband": 121.5,
    "PMR 446": 446.0, "ISM 433": 433.92, "ISM 868": 868.0,
    "ISM 915": 915.0, "GSM 900": 935.0, "GSM 1800": 1842.5,
    "UMTS": 2140.0, "LTE 2600": 2650.0, "GPS L1": 1575.42,
    "GPS L2": 1227.6, "WiFi 2.4": 2442.0, "WiFi 5": 5180.0,
    "Bluetooth": 2441.0, "DECT": 1881.8, "ADS-B": 1090.0,
    "ACARS": 129.125, "APRS": 144.8, "LoRa 868": 868.1,
    "Sigfox": 868.13, "NB-IoT": 900.0, "TETRA": 460.0,
    "DMR": 446.5, "P25": 851.0, "NOAA": 137.62,
    "HF 40m": 7.1, "HF 20m": 14.2, "HF 80m": 3.6,
}

SAMPLE_RATES = [
    ("0.25 MS/s", 250000), ("0.5 MS/s", 500000), ("1 MS/s", 1000000),
    ("2 MS/s", 2000000), ("4 MS/s", 4000000), ("6 MS/s", 6000000),
    ("8 MS/s", 8000000), ("10 MS/s", 10000000), ("16 MS/s", 16000000),
    ("20 MS/s", 20000000),
]

FREQ_STEPS = [
    ("1 Hz", 1e-6), ("10 Hz", 1e-5), ("100 Hz", 1e-4),
    ("1 kHz", 1e-3), ("5 kHz", 5e-3), ("10 kHz", 0.01),
    ("25 kHz", 0.025), ("50 kHz", 0.05), ("100 kHz", 0.1),
    ("200 kHz", 0.2), ("500 kHz", 0.5), ("1 MHz", 1.0),
    ("5 MHz", 5.0), ("10 MHz", 10.0),
]

DEMOD_MODES = ["Brak", "AM", "FM wąskie", "FM szerokie", "USB", "LSB", "CW"]


class ControlPanel(QWidget):
    """Pełny panel kontrolny HackRF."""

    sig_freq_changed = pyqtSignal(float)    # Hz
    sig_sr_changed = pyqtSignal(float)      # Hz
    sig_start = pyqtSignal()
    sig_stop = pyqtSignal()

    def __init__(self, config: dict, hackrf=None):
        super().__init__()
        self.config = config
        self.hackrf = hackrf
        self.running = False
        self.recording = False
        self.freq_step_mhz = 1.0
        self.meas_enabled = True
        self._rec_start = 0.0

        self._build_ui()
        self._load_from_config()

        # Timer statystyk
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(150)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)

        vl.addWidget(self._grp_device())
        vl.addWidget(self._grp_freq())
        vl.addWidget(self._grp_gains())
        vl.addWidget(self._grp_mode())
        vl.addWidget(self._grp_dsp())
        vl.addWidget(self._grp_recording())
        vl.addWidget(self._grp_stats())
        vl.addWidget(self._grp_presets())
        vl.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Sekcja: Urządzenie ────────────────────────────────────────────────────

    def _grp_device(self):
        grp = QGroupBox("🔌 Urządzenie")
        gl = QGridLayout(grp)

        self.lbl_dev_status = QLabel("Brak połączenia")
        self.lbl_dev_status.setStyleSheet("color:#ff4444;")
        self.btn_connect = QPushButton("Połącz")
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setCheckable(True)
        self.btn_start.clicked.connect(self._on_start_stop)
        self.btn_start.setStyleSheet("QPushButton:checked{background:#00aa44;color:#fff;}")

        gl.addWidget(QLabel("Status:"), 0, 0)
        gl.addWidget(self.lbl_dev_status, 0, 1, 1, 2)
        gl.addWidget(self.btn_connect, 1, 0)
        gl.addWidget(self.btn_start, 1, 1, 1, 2)
        return grp

    # ── Sekcja: Częstotliwość ─────────────────────────────────────────────────

    def _grp_freq(self):
        grp = QGroupBox("📡 Częstotliwość")
        vl = QVBoxLayout(grp)

        # Spinner
        hl = QHBoxLayout()
        self.spin_freq = QDoubleSpinBox()
        self.spin_freq.setRange(0.000001, 6000.0)
        self.spin_freq.setDecimals(6)
        self.spin_freq.setSuffix(" MHz")
        self.spin_freq.setValue(433.920)
        self.spin_freq.valueChanged.connect(self._on_freq_spin)
        hl.addWidget(self.spin_freq)

        self.cbo_step = QComboBox()
        for lbl, _ in FREQ_STEPS:
            self.cbo_step.addItem(lbl)
        self.cbo_step.setCurrentIndex(11)  # 1 MHz
        self.cbo_step.currentIndexChanged.connect(self._on_step_changed)
        hl.addWidget(self.cbo_step)
        vl.addLayout(hl)

        # +/- przyciski
        hl2 = QHBoxLayout()
        btn_minus = QPushButton("◀ −")
        btn_minus.clicked.connect(lambda: self._step_freq(-1))
        btn_plus = QPushButton("+ ▶")
        btn_plus.clicked.connect(lambda: self._step_freq(1))
        hl2.addWidget(btn_minus)
        hl2.addWidget(btn_plus)
        vl.addLayout(hl2)

        # Presety
        self.cbo_preset = QComboBox()
        self.cbo_preset.addItem("— Preset —")
        for name in BAND_PRESETS:
            self.cbo_preset.addItem(name)
        self.cbo_preset.currentTextChanged.connect(self._on_preset)
        vl.addWidget(self.cbo_preset)

        # Sample rate
        hl3 = QHBoxLayout()
        hl3.addWidget(QLabel("Sample rate:"))
        self.cbo_sr = QComboBox()
        for lbl, _ in SAMPLE_RATES:
            self.cbo_sr.addItem(lbl)
        self.cbo_sr.setCurrentIndex(3)  # 2 MS/s
        self.cbo_sr.currentIndexChanged.connect(self._on_sr_changed)
        hl3.addWidget(self.cbo_sr)
        vl.addLayout(hl3)

        return grp

    # ── Sekcja: Wzmocnienia ───────────────────────────────────────────────────

    def _grp_gains(self):
        grp = QGroupBox("📶 Wzmocnienia")
        gl = QGridLayout(grp)

        self.sld_lna = self._make_slider(0, 40, 8, step=8)
        self.sld_vga = self._make_slider(0, 62, 2, step=2)
        self.sld_txg = self._make_slider(0, 47, 1, step=1)

        self.lbl_lna = QLabel("16 dB")
        self.lbl_vga = QLabel("20 dB")
        self.lbl_txg = QLabel("20 dB")

        self.sld_lna.valueChanged.connect(lambda v: self._gain_changed("lna", v, self.lbl_lna))
        self.sld_vga.valueChanged.connect(lambda v: self._gain_changed("vga", v, self.lbl_vga))
        self.sld_txg.valueChanged.connect(lambda v: self._gain_changed("tx", v, self.lbl_txg))

        self.chk_amp = QCheckBox("Amp +14dB")
        self.chk_amp.toggled.connect(self._on_amp)

        gl.addWidget(QLabel("LNA:"), 0, 0)
        gl.addWidget(self.sld_lna, 0, 1)
        gl.addWidget(self.lbl_lna, 0, 2)
        gl.addWidget(QLabel("VGA:"), 1, 0)
        gl.addWidget(self.sld_vga, 1, 1)
        gl.addWidget(self.lbl_vga, 1, 2)
        gl.addWidget(QLabel("TX:"), 2, 0)
        gl.addWidget(self.sld_txg, 2, 1)
        gl.addWidget(self.lbl_txg, 2, 2)
        gl.addWidget(self.chk_amp, 3, 0, 1, 3)
        return grp

    # ── Sekcja: Tryb pracy ────────────────────────────────────────────────────

    def _grp_mode(self):
        grp = QGroupBox("⚙️ Tryb pracy")
        gl = QGridLayout(grp)

        self.chk_tx = QCheckBox("TX (nadawanie)")
        self.chk_tx.toggled.connect(self._on_tx_toggle)

        self.cbo_demod = QComboBox()
        for m in DEMOD_MODES:
            self.cbo_demod.addItem(m)
        self.cbo_demod.currentTextChanged.connect(self._on_demod)

        self.chk_squelch = QCheckBox("Squelch")
        self.spin_squelch = QSpinBox()
        self.spin_squelch.setRange(-120, 0)
        self.spin_squelch.setValue(-80)
        self.spin_squelch.setSuffix(" dBm")

        gl.addWidget(self.chk_tx, 0, 0, 1, 2)
        gl.addWidget(QLabel("Demod:"), 1, 0)
        gl.addWidget(self.cbo_demod, 1, 1)
        gl.addWidget(self.chk_squelch, 2, 0)
        gl.addWidget(self.spin_squelch, 2, 1)
        return grp

    # ── Sekcja: DSP ───────────────────────────────────────────────────────────

    def _grp_dsp(self):
        grp = QGroupBox("🔧 DSP")
        gl = QGridLayout(grp)

        self.cbo_fft = QComboBox()
        for n in ["256", "512", "1024", "2048", "4096", "8192"]:
            self.cbo_fft.addItem(f"FFT {n}", int(n))
        self.cbo_fft.setCurrentIndex(2)

        self.sld_avg = self._make_slider(1, 20, 1)
        self.lbl_avg = QLabel("α 0.10")
        self.sld_avg.valueChanged.connect(
            lambda v: self.lbl_avg.setText(f"α {v/100:.2f}") or
            self.config.update({"avg_alpha": v / 100})
        )
        self.sld_avg.setValue(10)

        self.chk_dc = QCheckBox("DC Notch")
        self.chk_dc.setChecked(True)
        self.chk_hanning = QCheckBox("Hanning Window")
        self.chk_hanning.setChecked(True)

        gl.addWidget(QLabel("FFT:"), 0, 0)
        gl.addWidget(self.cbo_fft, 0, 1, 1, 2)
        gl.addWidget(QLabel("Avg:"), 1, 0)
        gl.addWidget(self.sld_avg, 1, 1)
        gl.addWidget(self.lbl_avg, 1, 2)
        gl.addWidget(self.chk_dc, 2, 0)
        gl.addWidget(self.chk_hanning, 2, 1)
        return grp

    # ── Sekcja: Nagrywanie IQ ─────────────────────────────────────────────────

    def _grp_recording(self):
        grp = QGroupBox("⏺ Nagrywanie IQ")
        vl = QVBoxLayout(grp)

        hl = QHBoxLayout()
        self.btn_rec = QPushButton("⏺ Nagraj")
        self.btn_rec.setCheckable(True)
        self.btn_rec.clicked.connect(self._on_record)
        self.lbl_rec_time = QLabel("00:00")
        self.lbl_rec_size = QLabel("0 MB")
        hl.addWidget(self.btn_rec)
        hl.addWidget(self.lbl_rec_time)
        hl.addWidget(self.lbl_rec_size)
        vl.addLayout(hl)

        hl2 = QHBoxLayout()
        self.edt_rec_dir = QLineEdit(self.config.get("recording_dir", "recordings"))
        btn_browse = QPushButton("📂")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self._browse_rec_dir)
        hl2.addWidget(QLabel("Folder:"))
        hl2.addWidget(self.edt_rec_dir)
        hl2.addWidget(btn_browse)
        vl.addLayout(hl2)

        self.cbo_format = QComboBox()
        self.cbo_format.addItems(["CS8 (HackRF)", "CF32 (float)", "SigMF"])
        vl.addWidget(self.cbo_format)

        return grp

    # ── Sekcja: Statystyki ────────────────────────────────────────────────────

    def _grp_stats(self):
        grp = QGroupBox("📊 Live Stats")
        gl = QGridLayout(grp)

        self.lbl_dbm = QLabel("— dBm")
        self.lbl_sps = QLabel("— Sp/s")
        self.lbl_lat = QLabel("— ms")
        self.lbl_drop = QLabel("Drop: 0")
        self.lbl_of = QLabel("OF: 0")

        self.btn_meas = QPushButton("📶 POMIARY ON")
        self.btn_meas.setCheckable(True)
        self.btn_meas.setChecked(True)
        self.btn_meas.clicked.connect(self._on_meas_toggle)

        for i, (lbl_text, lbl_val) in enumerate([
            ("Sygnał:", self.lbl_dbm), ("Sp/s:", self.lbl_sps),
            ("Latency:", self.lbl_lat), ("", self.lbl_drop), ("", self.lbl_of)
        ]):
            gl.addWidget(QLabel(lbl_text), i, 0)
            gl.addWidget(lbl_val, i, 1)

        gl.addWidget(self.btn_meas, 5, 0, 1, 2)

        self.bar_signal = QProgressBar()
        self.bar_signal.setRange(0, 100)
        self.bar_signal.setValue(0)
        self.bar_signal.setTextVisible(False)
        self.bar_signal.setFixedHeight(8)
        self.bar_signal.setStyleSheet(
            "QProgressBar::chunk{background:#00bfff;}"
        )
        gl.addWidget(self.bar_signal, 6, 0, 1, 2)
        return grp

    # ── Sekcja: Presety JSON ──────────────────────────────────────────────────

    def _grp_presets(self):
        grp = QGroupBox("💾 Presety konfiguracji")
        hl = QHBoxLayout(grp)
        btn_save = QPushButton("💾 Zapisz")
        btn_load = QPushButton("📂 Wczytaj")
        btn_save.clicked.connect(self._save_preset)
        btn_load.clicked.connect(self._load_preset)
        hl.addWidget(btn_save)
        hl.addWidget(btn_load)
        return grp

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_slider(self, mn, mx, val, step=1):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(mn, mx)
        s.setValue(val)
        s.setSingleStep(step)
        s.setPageStep(step)
        return s

    def _load_from_config(self):
        self.spin_freq.setValue(self.config.get("center_freq", 433920000) / 1e6)
        self.sld_lna.setValue(self.config.get("lna_gain", 16))
        self.sld_vga.setValue(self.config.get("vga_gain", 20))
        self.sld_txg.setValue(self.config.get("tx_gain", 20))

    # ── Sloty ─────────────────────────────────────────────────────────────────

    def _on_connect(self):
        if self.hackrf:
            ok = self.hackrf.connect()
            if ok:
                self.lbl_dev_status.setText("HackRF ✅ Połączony")
                self.lbl_dev_status.setStyleSheet("color:#00ff88;")
            else:
                self.lbl_dev_status.setText("DEMO (brak HackRF)")
                self.lbl_dev_status.setStyleSheet("color:#ffaa00;")

    def _on_start_stop(self, checked: bool):
        if checked:
            self.running = True
            self.btn_start.setText("■ STOP")
            self.sig_start.emit()
        else:
            self.running = False
            self.btn_start.setText("▶ START")
            self.sig_stop.emit()

    def _on_freq_spin(self, val_mhz: float):
        self.config["center_freq"] = int(val_mhz * 1e6)
        self.sig_freq_changed.emit(val_mhz * 1e6)

    def _step_freq(self, direction: int):
        current = self.spin_freq.value()
        self.spin_freq.setValue(current + direction * self.freq_step_mhz)

    def _on_step_changed(self, idx: int):
        self.freq_step_mhz = FREQ_STEPS[idx][1]

    def _on_preset(self, name: str):
        if name in BAND_PRESETS:
            self.spin_freq.setValue(BAND_PRESETS[name])
            self.cbo_preset.setCurrentIndex(0)

    def _on_sr_changed(self, idx: int):
        sr = SAMPLE_RATES[idx][1]
        self.config["sample_rate"] = sr
        self.sig_sr_changed.emit(float(sr))

    def _gain_changed(self, kind: str, val: int, lbl: QLabel):
        lbl.setText(f"{val} dB")
        if kind == "lna":
            self.config["lna_gain"] = val
        elif kind == "vga":
            self.config["vga_gain"] = val
        elif kind == "tx":
            self.config["tx_gain"] = val
        if self.hackrf and self.running:
            getattr(self.hackrf, f"set_{kind}_gain", lambda v: None)(val)

    def _on_amp(self, checked: bool):
        if self.hackrf:
            self.hackrf.set_amp(checked)

    def _on_tx_toggle(self, checked: bool):
        self.config["tx_enabled"] = checked
        if self.hackrf:
            self.hackrf.set_tx_mode(checked)

    def _on_demod(self, mode: str):
        if self.hackrf:
            self.hackrf.set_demod(mode)

    def _on_record(self, checked: bool):
        if checked:
            self.recording = True
            self._rec_start = time.time()
            self.btn_rec.setText("⏹ Stop")
            self.btn_rec.setStyleSheet("background:#aa0000;color:#fff;")
        else:
            self.recording = False
            self.btn_rec.setText("⏺ Nagraj")
            self.btn_rec.setStyleSheet("")

    def _on_meas_toggle(self, checked: bool):
        self.meas_enabled = checked
        if checked:
            self.btn_meas.setText("📶 POMIARY ON")
            self.btn_meas.setStyleSheet("background:#004400;color:#00ff88;")
        else:
            self.btn_meas.setText("📵 POMIARY OFF")
            self.btn_meas.setStyleSheet("background:#440000;color:#ff4444;")

    def _browse_rec_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Wybierz folder nagrań")
        if d:
            self.edt_rec_dir.setText(d)
            self.config["recording_dir"] = d

    def _save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz preset", "", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                json.dump(self.config, f, indent=2)

    def _load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wczytaj preset", "", "JSON (*.json)")
        if path:
            try:
                with open(path) as f:
                    data = json.load(f)
                self.config.update(data)
                self._load_from_config()
            except Exception as e:
                pass

    def _update_stats(self):
        if not self.meas_enabled:
            return

        # Nagrywanie timer
        if self.recording:
            elapsed = int(time.time() - self._rec_start)
            m, s = divmod(elapsed, 60)
            self.lbl_rec_time.setText(f"{m:02d}:{s:02d}")
            size_mb = elapsed * self.config.get("sample_rate", 2e6) * 2 / 1e6
            self.lbl_rec_size.setText(f"{size_mb:.0f} MB")

        # Statystyki urządzenia
        if self.hackrf and self.running:
            try:
                dbm = self.hackrf.get_signal_level()
                lat = self.hackrf.get_latency_ms()
                sps = self.hackrf.get_samples_per_sec()
                drops = self.hackrf.get_drop_count()
                of = self.hackrf.get_overflow_count()

                if dbm is not None:
                    self.lbl_dbm.setText(f"{dbm:.1f} dBm")
                    pct = max(0, min(100, int((dbm + 100) * 1.5)))
                    self.bar_signal.setValue(pct)
                if lat is not None:
                    self.lbl_lat.setText(f"{lat:.1f} ms")
                if sps is not None:
                    self.lbl_sps.setText(f"{sps/1e6:.2f}M Sp/s")
                if drops is not None:
                    self.lbl_drop.setText(f"Drop: {drops}")
                if of is not None:
                    self.lbl_of.setText(f"OF: {of}")
            except Exception:
                pass
