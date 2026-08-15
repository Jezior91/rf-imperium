"""RF Imperium — TDOA Triangulator (2× HackRF lub SpecAn)"""
import numpy as np
from scipy.optimize import minimize
from typing import Optional


C_SPEED = 3e8   # prędkość światła [m/s]


class TDOATriangulator:
    def __init__(self):
        self.receivers: list[dict] = []
        self.measurements: list[dict] = []

    def add_receiver(self, x_m: float, y_m: float, name="RX"):
        self.receivers.append({"x": x_m, "y": y_m, "name": name,
                               "idx": len(self.receivers)})

    def clear_receivers(self):
        self.receivers = []
        self.measurements = []

    def add_tdoa(self, rx1_idx: int, rx2_idx: int, time_diff_s: float):
        """Dodaj pomiar różnicy czasu odbioru między dwoma odbiornikami"""
        self.measurements.append({
            "rx1": rx1_idx, "rx2": rx2_idx, "dt": time_diff_s
        })

    def compute_tdoa(self, iq1: np.ndarray, iq2: np.ndarray,
                     sample_rate=2e6) -> float:
        """Oblicz TDOA metodą korelacji krzyżowej (XCORR)"""
        n = min(len(iq1), len(iq2), 65536)
        s1 = iq1[:n]; s2 = iq2[:n]
        # GCC-PHAT (Generalized Cross-Correlation with Phase Transform)
        F1 = np.fft.fft(s1)
        F2 = np.fft.fft(s2)
        R = F1 * np.conj(F2)
        denom = np.abs(R) + 1e-12
        R_phat = R / denom
        corr = np.fft.ifft(R_phat)
        lag = int(np.argmax(np.abs(corr)))
        if lag > n // 2:
            lag -= n
        return float(lag / sample_rate)

    def locate(self) -> dict:
        if len(self.receivers) < 2:
            return {"error": "Potrzeba min. 2 odbiorników"}
        if not self.measurements:
            return {"error": "Brak pomiarów TDOA — dodaj przynajmniej 1"}

        def cost(pos):
            x, y = pos
            total = 0.0
            for m in self.measurements:
                r1 = self.receivers[m["rx1"]]
                r2 = self.receivers[m["rx2"]]
                d1 = np.sqrt((x - r1["x"]) ** 2 + (y - r1["y"]) ** 2)
                d2 = np.sqrt((x - r2["x"]) ** 2 + (y - r2["y"]) ** 2)
                dt_est = (d1 - d2) / C_SPEED
                total += (dt_est - m["dt"]) ** 2
            return total

        # Punkt startowy — centroid odbiorników
        x0 = np.mean([r["x"] for r in self.receivers])
        y0 = np.mean([r["y"] for r in self.receivers])

        res = minimize(
            cost, [x0, y0], method="Nelder-Mead",
            options={"xatol": 0.1, "fatol": 1e-16, "maxiter": 50000}
        )
        x_est, y_est = res.x
        residual_m = np.sqrt(res.fun) * C_SPEED if res.fun >= 0 else float("nan")

        return {
            "x_m": round(float(x_est), 2),
            "y_m": round(float(y_est), 2),
            "residual_m": round(residual_m, 2),
            "converged": bool(res.success),
            "iterations": int(res.nit),
        }

    def to_gps(self, x_m: float, y_m: float,
               origin_lat: float, origin_lon: float) -> tuple:
        """Przelicz współrzędne kartezjańskie na GPS"""
        lat = origin_lat + (y_m / 111111.0)
        lon = origin_lon + (x_m / (111111.0 * np.cos(np.radians(origin_lat))))
        return round(lat, 7), round(lon, 7)

    def get_hyperbola_points(self, rx1_idx: int, rx2_idx: int,
                              dt_s: float, n_pts=200) -> np.ndarray:
        """Zwraca punkty hiperboli TDOA do wizualizacji"""
        r1 = self.receivers[rx1_idx]
        r2 = self.receivers[rx2_idx]
        d_diff = dt_s * C_SPEED          # różnica odległości [m]
        cx = (r1["x"] + r2["x"]) / 2
        cy = (r1["y"] + r2["y"]) / 2
        baseline = np.sqrt((r2["x"] - r1["x"])**2 + (r2["y"] - r1["y"])**2)
        a = abs(d_diff) / 2
        if baseline <= 2 * a:
            return np.array([])
        c = baseline / 2
        b = np.sqrt(c ** 2 - a ** 2)
        t = np.linspace(-5 * b, 5 * b, n_pts)
        x_hyp = a * np.cosh(np.linspace(-2, 2, n_pts))
        y_hyp = b * np.sinh(np.linspace(-2, 2, n_pts))
        if d_diff < 0:
            x_hyp = -x_hyp
        angle = np.arctan2(r2["y"] - r1["y"], r2["x"] - r1["x"])
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        x_rot = cos_a * x_hyp - sin_a * y_hyp + cx
        y_rot = sin_a * x_hyp + cos_a * y_hyp + cy
        return np.column_stack([x_rot, y_rot])
