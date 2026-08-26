"""RF Imperium v5.0 MAX — MainWindow (PyQt6)"""
import json
import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QLabel, QSplitter, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

from src.ui.spectrum_widget import SpectrumWidget
from src.ui.waterfall_widget import WaterfallWidget
from src.ui.control_panel import ControlPanel
from src.ui.decoder_panel import DecoderPanel
from src.ui.spoofer_panel import SpooferPanel
from src.ui.sweep_panel import SweepPanel
from src.ui.settings_panel import SettingsPanel
from src.core.hackrf_controller import HackRFController
from src.core.dsp_engine import DSPEngine


DARK_STYLE = """
QMainWindow, QWidget { background: #0d0f1a; color: #e0e0e0; font-family: Consolas, monospace; }
QTabWidget::pane { border: 1px solid #1e2840; background: #0d0f1a; }
QTabBar::tab { background: #111827; color: #8892a4; padding: 8px 18px; border: 1px solid #1e2840; }
QTabBar::tab:selected { background: #1a2340; color: #00bfff; border-bottom: 2px solid #00bfff; }
QTabBar::tab:hover { background: #16213e; color: #60cfff; }
QGroupBox { border: 1px solid #1e2840; border-radius: 4px; margin-top: 12px; padding: 6px; }
QGroupBox::title { color: #00bfff; subcontrol-origin: margin; left: 8px; }
QPushButton { background: #1a2340; color: #00bfff; border: 1px solid #00bfff; border-radius: 3px; padding: 5px 12px; }
QPushButton:hover { background: #0044aa; }
QPushButton:pressed { background: #003080; }
QPushButton:checked { background: #00bfff; color: #000; }
QSlider::groove:horizontal { background: #1e2840; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #00bfff; width: 14px; height: 14px; border-radius: 7px; margin: -4px 0; }
QSlider::sub-page:horizontal { background: #0044aa; border-radius: 3px; }
QComboBox { background: #1a2340; color: #e0e0e0; border: 1px solid #1e2840; padding: 3px 8px; border-radius: 3px; }
QComboBox::drop-down { border: none; }
QLineEdit { background: #111827; color: #e0e0e0; border: 1px solid #1e2840; padding: 3px 6px; border-radius: 3px; }
QSpinBox, QDoubleSpinBox { background: #111827; color: #e0e0e0; border: 1px solid #1e2840; padding: 3px 6px; border-radius: 3px; }
QStatusBar { background: #080a12; color: #8892a4; border-top: 1px solid #1e2840; }
QScrollBar:vertical { background: #111827; width: 10px; }
QScrollBar::handle:vertical { background: #1e2840; border-radius: 5px; min-height: 20px; }
QLabel { color: #c0c8d8; }
QTextEdit { background: #080a12; color: #00ff88; border: 1px solid #1e2840; font-family: Consolas, monospace; font-size: 11px; }
"""


class MainWindow(QMainWindow):
    """RF Imperium v5.0 MAX — główne okno aplikacji."""

    sig_freq_changed = pyqtSignal(float)

    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config_path = config_path
        self.config = self._load_config()

        # Silnik i kontroler
        self.hackrf = HackRFController(self.config)
        self.dsp = DSPEngine(self.config)

        self._init_ui()
        self._apply_style()
        self._connect_signals()
        self._start_timers()

        # Auto-connect jeśli dostępne
        QTimer.singleShot(200, self._auto_connect)

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        defaults = {
            "center_freq": 433920000,
            "sample_rate": 2000000,
            "lna_gain": 16,
            "vga_gain": 20,
            "tx_gain": 20,
            "tx_enabled": False,
            "openai_key": "",
            "openai_model": "gpt-4o",
            "sa_resource": "",
            "sg_resource": "",
            "recording_dir": "recordings",
            "fft_size": 1024,
            "avg_alpha": 0.1,
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def _save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.status_bar.showMessage(f"Błąd zapisu config: {e}", 3000)

    # ── UI Init ───────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle("RF Imperium v5.0 MAX — HackRF Panel [1Hz–6GHz]")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 950)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ── Lewy panel: widgety wizualizacji ──────────────────────────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        self.spectrum = SpectrumWidget(self.config)
        self.waterfall = WaterfallWidget(self.config)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.spectrum)
        splitter.addWidget(self.waterfall)
        splitter.setSizes([420, 280])

        left_layout.addWidget(splitter)

        # ── Prawy panel: zakładki kontrolne ───────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setFixedWidth(420)

        self.control_panel = ControlPanel(self.config, self.hackrf)
        self.decoder_panel = DecoderPanel(self.config)
        self.spoofer_panel = SpooferPanel(self.config, self.hackrf)
        self.sweep_panel = SweepPanel(self.config, self.hackrf)
        self.settings_panel = SettingsPanel(self.config, self._save_config)

        self.tabs.addTab(self.control_panel, "🎛 Kontrola")
        self.tabs.addTab(self.decoder_panel, "🔬 Dekoder")
        self.tabs.addTab(self.spoofer_panel, "⚔️ Spoofer")
        self.tabs.addTab(self.sweep_panel, "🔍 Sweep")
        self.tabs.addTab(self.settings_panel, "⚙️ Ustawienia")

        main_layout.addWidget(left_widget, stretch=1)
        main_layout.addWidget(self.tabs)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_device = QLabel("Urządzenie: —")
        self.lbl_freq = QLabel("Częst: —")
        self.lbl_sr = QLabel("SR: —")
        self.lbl_dbm = QLabel("dBm: —")
        self.lbl_lat = QLabel("Lat: —")

        for lbl in [self.lbl_device, self.lbl_freq, self.lbl_sr, self.lbl_dbm, self.lbl_lat]:
            lbl.setFont(QFont("Consolas", 9))
            self.status_bar.addPermanentWidget(lbl)

    def _apply_style(self):
        self.setStyleSheet(DARK_STYLE)

    # ── Sygnały ───────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.control_panel.sig_freq_changed.connect(self._on_freq_changed)
        self.control_panel.sig_sr_changed.connect(self._on_sr_changed)
        self.control_panel.sig_start.connect(self._on_start)
        self.control_panel.sig_stop.connect(self._on_stop)
        self.hackrf.sig_data.connect(self._on_iq_data)
        self.hackrf.sig_status.connect(self._on_device_status)

    def _start_timers(self):
        self.timer_stats = QTimer()
        self.timer_stats.timeout.connect(self._update_status)
        self.timer_stats.start(150)

    # ── Sloty ─────────────────────────────────────────────────────────────────

    def _auto_connect(self):
        try:
            ok = self.hackrf.connect()
            if ok:
                self.lbl_device.setText("Urządzenie: HackRF ✅")
                self.status_bar.showMessage("HackRF połączony", 2000)
            else:
                self.lbl_device.setText("Urządzenie: DEMO")
                self.status_bar.showMessage("Tryb DEMO (brak HackRF)", 3000)
        except Exception as e:
            self.lbl_device.setText("Urządzenie: DEMO")

    def _on_freq_changed(self, freq_hz: float):
        self.config["center_freq"] = int(freq_hz)
        self.hackrf.set_freq(freq_hz)
        self.spectrum.set_center_freq(freq_hz)
        self.waterfall.set_center_freq(freq_hz)
        self.lbl_freq.setText(f"Częst: {freq_hz/1e6:.4f} MHz")

    def _on_sr_changed(self, sr: float):
        self.config["sample_rate"] = int(sr)
        self.hackrf.set_sample_rate(sr)
        self.lbl_sr.setText(f"SR: {sr/1e6:.1f} MS/s")

    def _on_start(self):
        self.hackrf.start_rx()
        self.spectrum.start()
        self.waterfall.start()
        self.status_bar.showMessage("Odbiór uruchomiony ▶", 2000)

    def _on_stop(self):
        self.hackrf.stop_rx()
        self.spectrum.stop()
        self.waterfall.stop()
        self.status_bar.showMessage("Odbiór zatrzymany ■", 2000)

    def _on_iq_data(self, iq_data):
        fft_data = self.dsp.process(iq_data)
        self.spectrum.update_data(fft_data)
        self.waterfall.update_data(fft_data)

    def _on_device_status(self, msg: str):
        self.status_bar.showMessage(msg, 2000)

    def _update_status(self):
        dbm = self.hackrf.get_signal_level()
        lat = self.hackrf.get_latency_ms()
        if dbm is not None:
            self.lbl_dbm.setText(f"dBm: {dbm:.1f}")
        if lat is not None:
            self.lbl_lat.setText(f"Lat: {lat:.1f}ms")

    # ── Menu / Close ──────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_config()
        try:
            self.hackrf.disconnect()
        except Exception:
            pass
        event.accept()
