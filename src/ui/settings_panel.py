"""RF Imperium — Settings Panel"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                               QPushButton, QLineEdit, QGroupBox, QComboBox,
                               QSpinBox, QDoubleSpinBox, QCheckBox,
                               QFileDialog, QTabWidget)
from PyQt6.QtCore import pyqtSignal
import json, os


class SettingsPanel(QWidget):
    sig_saved = pyqtSignal(dict)

    def __init__(self, config_path="config.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self._cfg = {}
        self._setup_ui()
        self.load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4,4,4,4)
        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #333;background:#080818;}"
            "QTabBar::tab{background:#1a1a2e;color:#aaa;padding:6px 12px;border:1px solid #333;}"
            "QTabBar::tab:selected{background:#0a0a2e;color:#0cf;}")

        # API tab
        api_w = QWidget(); ag = QVBoxLayout(api_w)
        grp_ai = QGroupBox("OpenAI API"); grp_ai.setStyleSheet("QGroupBox{color:#0f8;font-weight:bold;}")
        ga = QGridLayout(grp_ai)
        self._edit_openai_key = QLineEdit(); self._edit_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_openai_key.setPlaceholderText("sk-proj-...")
        self._edit_openai_key.setStyleSheet("background:#0a1a0a;color:#0f0;font-family:monospace;")
        self._combo_model = QComboBox()
        self._combo_model.addItems(["gpt-4o","gpt-4o-mini","gpt-4-turbo","gpt-3.5-turbo"])
        self._combo_model.setStyleSheet("background:#1a1a2e;color:#fff;")
        ga.addWidget(QLabel("API Key:"),0,0); ga.addWidget(self._edit_openai_key,0,1)
        ga.addWidget(QLabel("Model:"),1,0); ga.addWidget(self._combo_model,1,1)
        ag.addWidget(grp_ai); ag.addStretch()
        tabs.addTab(api_w,"API")

        # Device tab
        dev_w = QWidget(); dg = QVBoxLayout(dev_w)
        grp_hrf = QGroupBox("HackRF"); grp_hrf.setStyleSheet("QGroupBox{color:#0cf;font-weight:bold;}")
        gh = QGridLayout(grp_hrf)
        self._spin_dev_idx = QSpinBox(); self._spin_dev_idx.setRange(0,7)
        self._spin_dev_idx.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_tx_gain = QSpinBox(); self._spin_tx_gain.setRange(0,47)
        self._spin_tx_gain.setValue(20); self._spin_tx_gain.setSuffix(" dB TX VGA")
        self._spin_tx_gain.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._chk_bias_t = QCheckBox("Bias-T (antena aktywna)")
        self._chk_bias_t.setStyleSheet("color:#fa0;")
        self._chk_amp = QCheckBox("Enable RF Amplifier")
        self._chk_amp.setStyleSheet("color:#fa0;")
        gh.addWidget(QLabel("Device idx:"),0,0); gh.addWidget(self._spin_dev_idx,0,1)
        gh.addWidget(QLabel("TX gain:"),1,0); gh.addWidget(self._spin_tx_gain,1,1)
        gh.addWidget(self._chk_bias_t,2,0,1,2)
        gh.addWidget(self._chk_amp,3,0,1,2)
        dg.addWidget(grp_hrf)

        grp_visa = QGroupBox("VISA / SCPI"); grp_visa.setStyleSheet("QGroupBox{color:#0cf;font-weight:bold;}")
        gv = QGridLayout(grp_visa)
        self._edit_sa_res = QLineEdit(); self._edit_sa_res.setPlaceholderText("USB0::0x....::INSTR")
        self._edit_sa_res.setStyleSheet("background:#0a0a1e;color:#0ff;font-family:monospace;")
        self._edit_sg_res = QLineEdit(); self._edit_sg_res.setPlaceholderText("TCPIP::192.168.1.x::INSTR")
        self._edit_sg_res.setStyleSheet("background:#0a0a1e;color:#0ff;font-family:monospace;")
        gv.addWidget(QLabel("SpecAn VISA:"),0,0); gv.addWidget(self._edit_sa_res,0,1)
        gv.addWidget(QLabel("SigGen VISA:"),1,0); gv.addWidget(self._edit_sg_res,1,1)
        dg.addWidget(grp_visa)
        dg.addStretch()
        tabs.addTab(dev_w,"Urządzenia")

        # Recording tab
        rec_w = QWidget(); rg = QVBoxLayout(rec_w)
        grp_rec = QGroupBox("IQ Recording"); grp_rec.setStyleSheet("QGroupBox{color:#f80;font-weight:bold;}")
        gr = QGridLayout(grp_rec)
        self._edit_rec_dir = QLineEdit(); self._edit_rec_dir.setText("recordings")
        self._edit_rec_dir.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._btn_rec_browse = QPushButton("Browse")
        self._btn_rec_browse.setStyleSheet("background:#333;color:#ccc;border:1px solid #555;")
        self._btn_rec_browse.clicked.connect(self._browse_rec)
        gr.addWidget(QLabel("Katalog:"),0,0); gr.addWidget(self._edit_rec_dir,0,1)
        gr.addWidget(self._btn_rec_browse,0,2)
        rg.addWidget(grp_rec); rg.addStretch()
        tabs.addTab(rec_w,"Nagrywanie")

        # DSP tab
        dsp_w = QWidget(); dp = QVBoxLayout(dsp_w)
        grp_dsp = QGroupBox("DSP"); grp_dsp.setStyleSheet("QGroupBox{color:#a0f;font-weight:bold;}")
        gd = QGridLayout(grp_dsp)
        self._spin_fft = QComboBox()
        for s in ["512","1024","2048","4096"]: self._spin_fft.addItem(s,int(s))
        self._spin_fft.setCurrentIndex(1)
        self._spin_fft.setStyleSheet("background:#1a1a2e;color:#fff;")
        self._spin_avg = QDoubleSpinBox(); self._spin_avg.setRange(0.01,1.0)
        self._spin_avg.setValue(0.1); self._spin_avg.setSingleStep(0.01)
        self._spin_avg.setStyleSheet("background:#1a1a2e;color:#fff;")
        gd.addWidget(QLabel("FFT size:"),0,0); gd.addWidget(self._spin_fft,0,1)
        gd.addWidget(QLabel("Avg alpha:"),1,0); gd.addWidget(self._spin_avg,1,1)
        dp.addWidget(grp_dsp); dp.addStretch()
        tabs.addTab(dsp_w,"DSP")

        layout.addWidget(tabs)

        # Save/Load
        btn_row = QVBoxLayout()
        self._btn_save = QPushButton("💾 Zapisz ustawienia")
        self._btn_save.setStyleSheet("background:#003300;color:#0f0;border:2px solid #0a0;font-weight:bold;font-size:12px;padding:6px;")
        self._btn_save.clicked.connect(self.save)
        self._btn_load = QPushButton("📂 Wczytaj ustawienia")
        self._btn_load.setStyleSheet("background:#000033;color:#88f;border:2px solid #44f;font-size:12px;padding:6px;")
        self._btn_load.clicked.connect(self.load)
        btn_row.addWidget(self._btn_save); btn_row.addWidget(self._btn_load)
        layout.addLayout(btn_row)

    def _browse_rec(self):
        d = QFileDialog.getExistingDirectory(self,"Katalog nagrań")
        if d: self._edit_rec_dir.setText(d)

    def get_config(self) -> dict:
        return {
            "openai_key": self._edit_openai_key.text(),
            "openai_model": self._combo_model.currentText(),
            "hackrf_device_index": self._spin_dev_idx.value(),
            "tx_gain": self._spin_tx_gain.value(),
            "bias_t": self._chk_bias_t.isChecked(),
            "amp": self._chk_amp.isChecked(),
            "sa_resource": self._edit_sa_res.text(),
            "sg_resource": self._edit_sg_res.text(),
            "recording_dir": self._edit_rec_dir.text(),
            "fft_size": self._spin_fft.currentData(),
            "avg_alpha": self._spin_avg.value(),
        }

    def save(self):
        cfg = self.get_config()
        try:
            with open(self.config_path,"w",encoding="utf-8") as f:
                json.dump(cfg,f,indent=2)
            self.sig_saved.emit(cfg)
        except Exception as e:
            print(f"Settings save ERR: {e}")

    def load(self):
        if not os.path.exists(self.config_path): return
        try:
            with open(self.config_path,encoding="utf-8") as f:
                cfg = json.load(f)
            self._edit_openai_key.setText(cfg.get("openai_key",""))
            idx = self._combo_model.findText(cfg.get("openai_model","gpt-4o"))
            if idx>=0: self._combo_model.setCurrentIndex(idx)
            self._spin_dev_idx.setValue(cfg.get("hackrf_device_index",0))
            self._spin_tx_gain.setValue(cfg.get("tx_gain",20))
            self._chk_bias_t.setChecked(cfg.get("bias_t",False))
            self._chk_amp.setChecked(cfg.get("amp",False))
            self._edit_sa_res.setText(cfg.get("sa_resource",""))
            self._edit_sg_res.setText(cfg.get("sg_resource",""))
            self._edit_rec_dir.setText(cfg.get("recording_dir","recordings"))
            fi = self._spin_fft.findData(cfg.get("fft_size",1024))
            if fi>=0: self._spin_fft.setCurrentIndex(fi)
            self._spin_avg.setValue(cfg.get("avg_alpha",0.1))
            self._cfg = cfg
        except Exception as e:
            print(f"Settings load ERR: {e}")
