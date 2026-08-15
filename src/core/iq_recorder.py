"""RF Imperium — IQ Recorder / Playback (SigMF compatible)"""
import numpy as np, json, threading, time
from pathlib import Path
from datetime import datetime

IQ_DIR = Path.home() / ".rf_imperium" / "recordings"
IQ_DIR.mkdir(parents=True, exist_ok=True)


class IQRecorder:
    def __init__(self):
        self.recording = False
        self.playing = False
        self.buffer = []
        self._thread = None
        self.current_file = None
        self.sample_rate = 2e6
        self.center_freq = 433.92e6
        self.on_status = None

    def start_record(self, freq_hz, sample_rate=2e6, filename=None):
        self.center_freq = freq_hz
        self.sample_rate = sample_rate
        self.buffer = []
        self.recording = True
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(IQ_DIR / f"rec_{ts}_{int(freq_hz/1e6)}MHz.iq")
        self.current_file = filename
        if self.on_status:
            self.on_status(f"REC START: {filename}")
        return filename

    def feed(self, iq: np.ndarray):
        """Wywołaj z RX thread podczas nagrywania"""
        if self.recording:
            self.buffer.append(iq.astype(np.complex64).copy())

    def stop_record(self):
        self.recording = False
        if not self.buffer:
            return None
        data = np.concatenate(self.buffer)
        data.tofile(self.current_file)
        meta = {
            "global": {"core:datatype": "cf32_le",
                       "core:sample_rate": self.sample_rate,
                       "core:version": "1.0.0"},
            "captures": [{"core:sample_start": 0,
                           "core:frequency": self.center_freq,
                           "core:datetime": datetime.utcnow().isoformat()}],
            "annotations": []
        }
        with open(self.current_file + ".sigmf-meta", "w") as mf:
            json.dump(meta, mf, indent=2)
        mb = data.nbytes / 1e6
        if self.on_status:
            self.on_status(f"Zapisano {mb:.1f} MB -> {self.current_file}")
        self.buffer = []
        return self.current_file

    def list_recordings(self):
        files = sorted(IQ_DIR.glob("*.iq"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        result = []
        for f in files:
            meta_p = Path(str(f) + ".sigmf-meta")
            freq = 0
            if meta_p.exists():
                try:
                    m = json.loads(meta_p.read_text())
                    freq = m["captures"][0].get("core:frequency", 0)
                except Exception:
                    pass
            result.append({"path": str(f),
                           "size_mb": round(f.stat().st_size / 1e6, 2),
                           "freq_hz": freq, "name": f.name})
        return result

    def load_iq(self, path) -> np.ndarray:
        return np.fromfile(path, dtype=np.complex64)

    def start_playback(self, path, hackrf_tx_fn, loop=False):
        self.playing = True

        def _play():
            data = self.load_iq(path)
            chunk = 131072
            while self.playing:
                for i in range(0, len(data), chunk):
                    if not self.playing:
                        break
                    hackrf_tx_fn(data[i:i + chunk])
                    time.sleep(0.05)
                if not loop:
                    break
            self.playing = False
            if self.on_status:
                self.on_status("Playback zakończony")

        self._thread = threading.Thread(target=_play, daemon=True)
        self._thread.start()

    def stop_playback(self):
        self.playing = False

    def get_preview(self, path, max_samples=4096) -> np.ndarray:
        data = self.load_iq(path)
        step = max(1, len(data) // max_samples)
        return data[::step][:max_samples]

    def delete(self, path):
        Path(path).unlink(missing_ok=True)
        Path(path + ".sigmf-meta").unlink(missing_ok=True)
