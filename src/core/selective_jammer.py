"""RF Imperium — Selective Jammer (narrow-band, wąskopasmowy)"""
import numpy as np
import threading
import time
from scipy.signal import butter, lfilter


class SelectiveJammer:
    def __init__(self):
        self.running = False
        self._thread = None
        self.on_status = None

    def _make_noise(self, bandwidth_hz: float, sample_rate: float,
                    n_samples: int, jam_type="noise") -> np.ndarray:
        if jam_type == "noise":
            iq = ((np.random.randn(n_samples) +
                   1j * np.random.randn(n_samples)) * 0.5).astype(np.complex64)
        elif jam_type == "tone":
            t = np.arange(n_samples) / sample_rate
            iq = np.exp(2j * np.pi * 0 * t).astype(np.complex64)
        elif jam_type == "sweep":
            t = np.arange(n_samples) / sample_rate
            f = np.linspace(-bandwidth_hz / 2, bandwidth_hz / 2, n_samples)
            phase = np.cumsum(f) / sample_rate
            iq = np.exp(2j * np.pi * phase).astype(np.complex64)
        elif jam_type == "barrage":
            n_tones = 5
            iq = np.zeros(n_samples, dtype=np.complex64)
            for k in range(n_tones):
                f = (k - n_tones // 2) * bandwidth_hz / n_tones
                t = np.arange(n_samples) / sample_rate
                iq += np.exp(2j * np.pi * f * t).astype(np.complex64)
            iq /= n_tones
        elif jam_type == "chirp":
            t = np.arange(n_samples) / sample_rate
            f_inst = np.linspace(-bandwidth_hz / 2, bandwidth_hz / 2, n_samples)
            iq = np.exp(1j * 2 * np.pi * np.cumsum(f_inst) / sample_rate).astype(np.complex64)
        else:
            iq = np.zeros(n_samples, dtype=np.complex64)

        # Ogranicz do żądanej szerokości pasma
        if bandwidth_hz < sample_rate / 2:
            nyq = sample_rate / 2
            bw = bandwidth_hz / nyq
            if 0 < bw < 1:
                try:
                    b, a = butter(4, min(bw, 0.99), btype="low")
                    iq = lfilter(b, a, iq).astype(np.complex64)
                except Exception:
                    pass

        return iq

    def start_jam(self, target_freq_hz: float, bandwidth_hz: float,
                  hackrf_set_freq_fn, hackrf_tx_fn,
                  sample_rate=2e6, jam_type="noise", power=0.7):
        self.running = True

        def _jam():
            hackrf_set_freq_fn(target_freq_hz)
            if self.on_status:
                self.on_status(
                    f"JAM ON: {target_freq_hz/1e6:.3f} MHz  "
                    f"BW={bandwidth_hz/1e3:.0f} kHz  typ={jam_type}"
                )
            chunk = 131072
            while self.running:
                iq = self._make_noise(bandwidth_hz, sample_rate, chunk, jam_type) * power
                hackrf_tx_fn(iq)
                time.sleep(0.01)
            if self.on_status:
                self.on_status("JAM OFF")

        self._thread = threading.Thread(target=_jam, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def pulse_jam(self, target_freq_hz: float, bandwidth_hz: float,
                  hackrf_set_freq_fn, hackrf_tx_fn,
                  sample_rate=2e6, on_ms=100, off_ms=100, cycles=10,
                  jam_type="noise"):
        def _pulse():
            for _ in range(cycles):
                if not self.running:
                    break
                self.start_jam(target_freq_hz, bandwidth_hz,
                               hackrf_set_freq_fn, hackrf_tx_fn,
                               sample_rate, jam_type)
                time.sleep(on_ms / 1000)
                self.stop()
                time.sleep(off_ms / 1000)

        self.running = True
        threading.Thread(target=_pulse, daemon=True).start()
