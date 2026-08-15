"""RF Imperium — DSP Engine (FFT, Waterfall, AGC, Filtry)"""
import numpy as np
from scipy import signal as sp


class DSPEngine:
    def __init__(self, fft_size=1024):
        self.fft_size = fft_size
        self.window = np.blackman(fft_size).astype(np.float32)
        self.waterfall = np.full((128, fft_size), -120.0, dtype=np.float32)
        self.peak_hold = np.full(fft_size, -120.0, dtype=np.float32)
        self.avg_buf = np.full(fft_size, -120.0, dtype=np.float32)
        self.avg_alpha = 0.1
        self._buf = np.zeros(fft_size, dtype=np.complex64)

    def process(self, iq, sample_rate, center_freq) -> dict:
        n = self.fft_size
        if len(iq) >= n:
            seg = iq[-n:].astype(np.complex64)
        else:
            self._buf = np.roll(self._buf, -len(iq))
            self._buf[-len(iq):] = iq.astype(np.complex64)
            seg = self._buf.copy()
        fft = np.fft.fftshift(np.fft.fft(seg * self.window, n=n))
        power = (20*np.log10(np.abs(fft)/n+1e-12)).astype(np.float32)
        self.avg_buf = self.avg_alpha*power + (1-self.avg_alpha)*self.avg_buf
        self.peak_hold = np.maximum(self.peak_hold, power)
        self.waterfall = np.roll(self.waterfall, -1, axis=0)
        self.waterfall[-1] = power
        freqs = np.fft.fftshift(np.fft.fftfreq(n,1/sample_rate)) + center_freq
        peaks = self._find_peaks(power, freqs)
        return {"fft":power,"avg":self.avg_buf.copy(),"peak":self.peak_hold.copy(),
                "waterfall":self.waterfall.copy(),"freqs":freqs,"peaks":peaks,
                "center_freq":center_freq,"sample_rate":sample_rate}

    def _find_peaks(self, power, freqs, min_db=-80.0, min_distance=8):
        idx, _ = sp.find_peaks(power, height=min_db, distance=min_distance)
        return [{"freq_hz":float(freqs[i]),"freq_mhz":round(float(freqs[i])/1e6,4),
                 "power_dbm":round(float(power[i]),1)} for i in idx]

    def apply_agc(self, iq, target_db=-20.0):
        pwr = 10*np.log10(np.mean(np.abs(iq)**2)+1e-12)
        return (iq * 10**((target_db-pwr)/20.0)).astype(np.complex64)

    def lowpass(self, iq, cutoff_hz, sample_rate):
        fc = cutoff_hz/(sample_rate/2)
        if fc >= 1.0: return iq
        b,a = sp.butter(8, min(fc,0.99), btype="low")
        return sp.lfilter(b,a,iq).astype(np.complex64)

    def bandpass(self, iq, low_hz, high_hz, sample_rate):
        nyq = sample_rate/2; lo,hi = low_hz/nyq, high_hz/nyq
        if lo<=0 or hi>=1.0 or lo>=hi: return iq
        b,a = sp.butter(6,[lo,min(hi,0.99)],btype="band")
        return sp.lfilter(b,a,iq).astype(np.complex64)

    def notch(self, iq, freq_hz, sample_rate, Q=30.0):
        w0 = freq_hz/(sample_rate/2)
        if not (0<w0<1): return iq
        b,a = sp.iirnotch(w0, Q)
        return sp.lfilter(b,a,iq).astype(np.complex64)

    def decimate(self, iq, factor):
        if factor<=1: return iq
        return sp.decimate(iq,int(factor),ftype="fir",zero_phase=True).astype(np.complex64)

    def reset_peak(self): self.peak_hold[:] = -120.0
    def reset_avg(self): self.avg_buf[:] = -120.0
