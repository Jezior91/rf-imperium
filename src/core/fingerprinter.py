"""RF Imperium — Signal Fingerprinting (identyfikacja nadajnika)"""
import numpy as np
from scipy import signal as sp
import json
from pathlib import Path

FP_FILE = Path.home() / ".rf_imperium" / "fingerprints.json"


class Fingerprinter:
    def __init__(self):
        self.db = self._load()

    def _load(self) -> list:
        if FP_FILE.exists():
            try:
                return json.loads(FP_FILE.read_text())
            except Exception:
                pass
        return []

    def _save(self):
        FP_FILE.parent.mkdir(exist_ok=True)
        FP_FILE.write_text(json.dumps(self.db, indent=2))

    def extract_features(self, iq: np.ndarray, sample_rate=2e6) -> dict:
        if len(iq) < 512:
            return {}
        n = min(len(iq), 4096)
        chunk = iq[:n]

        # Spektralne
        fft = np.abs(np.fft.fft(chunk))
        fft_norm = fft / (fft.max() + 1e-12)
        idxs = np.arange(len(fft))
        centroid = float(np.sum(idxs * fft) / (np.sum(fft) + 1e-12))
        spread = float(np.sqrt(np.sum(((idxs - centroid) ** 2) * fft) / (np.sum(fft) + 1e-12)))

        # Fazowe
        phase = np.angle(chunk[:1024])
        phase_diff = np.diff(phase)
        phase_var = float(np.var(phase_diff))
        phase_kurt = float(
            np.mean((phase_diff - np.mean(phase_diff)) ** 4) /
            (np.var(phase_diff) ** 2 + 1e-12)
        )

        # Obwiednia
        env = np.abs(chunk)
        env_norm = env / (env.max() + 1e-12)
        kurtosis = float(
            np.mean((env - np.mean(env)) ** 4) / (np.var(env) ** 2 + 1e-12)
        )
        skewness = float(
            np.mean((env - np.mean(env)) ** 3) / (np.std(env) ** 3 + 1e-12)
        )

        # Czas narastania (rise time)
        above = np.where(env_norm > 0.9)[0]
        rise_time = float(above[0]) / sample_rate if len(above) > 0 else 0.0

        # Piki widmowe
        peaks, _ = sp.find_peaks(fft_norm, height=0.1, distance=5)
        bw_est = float(np.sum(fft_norm > 0.1) * sample_rate / len(fft))

        return {
            "spectral_centroid": round(centroid, 2),
            "spectral_spread": round(spread, 2),
            "phase_variance": round(phase_var, 6),
            "phase_kurtosis": round(phase_kurt, 3),
            "rise_time_s": round(rise_time, 9),
            "env_kurtosis": round(kurtosis, 3),
            "env_skewness": round(skewness, 3),
            "peak_count": int(len(peaks)),
            "bandwidth_est_hz": round(bw_est, 1),
            "mean_power": round(float(np.mean(np.abs(chunk) ** 2)), 6),
        }

    def save(self, name: str, iq: np.ndarray, freq_hz: float, notes="") -> dict:
        features = self.extract_features(iq)
        entry = {"name": name, "freq_hz": freq_hz,
                 "features": features, "notes": notes}
        # Replace if same name
        self.db = [e for e in self.db if e["name"] != name]
        self.db.append(entry)
        self._save()
        return entry

    def match(self, iq: np.ndarray, top_n=5) -> list:
        features = self.extract_features(iq)
        if not features or not self.db:
            return []
        keys = list(features.keys())
        vec = np.array([features[k] for k in keys], dtype=float)
        results = []
        for entry in self.db:
            ef = entry.get("features", {})
            evec = np.array([ef.get(k, 0) for k in keys], dtype=float)
            norm = np.linalg.norm(vec) * np.linalg.norm(evec)
            score = float(np.dot(vec, evec) / (norm + 1e-12)) if norm > 0 else 0.0
            results.append({
                "name": entry["name"],
                "score": round(score, 4),
                "freq_hz": entry.get("freq_hz", 0),
                "notes": entry.get("notes", ""),
            })
        results.sort(key=lambda x: -x["score"])
        return results[:top_n]

    def list_all(self) -> list:
        return self.db

    def delete(self, name: str):
        self.db = [e for e in self.db if e["name"] != name]
        self._save()
