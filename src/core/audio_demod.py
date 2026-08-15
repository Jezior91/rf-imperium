"""RF Imperium — Audio Demodulator (AM/FM/SSB/CW/DTMF/CTCSS)"""
import numpy as np
from scipy import signal as sp
import threading
import queue

AUDIO_RATE = 48000

DTMF_MAP = {
    (697, 1209): "1", (697, 1336): "2", (697, 1477): "3", (697, 1633): "A",
    (770, 1209): "4", (770, 1336): "5", (770, 1477): "6", (770, 1633): "B",
    (852, 1209): "7", (852, 1336): "8", (852, 1477): "9", (852, 1633): "C",
    (941, 1209): "*", (941, 1336): "0", (941, 1477): "#", (941, 1633): "D",
}

CTCSS_TONES = [
    67.0, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5, 94.8, 97.4, 100.0,
    103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3, 131.8, 136.5, 141.3,
    146.2, 151.4, 156.7, 162.2, 167.9, 173.8, 179.9, 186.2, 192.8, 203.5, 250.3,
]


class AudioDemod:
    def __init__(self):
        self.mode = "FM"
        self.volume = 0.7
        self.squelch_db = -60.0
        self.running = False
        self._q = queue.Queue(maxsize=20)
        self._thread = None
        self._out = None
        self.dtmf_buffer = []
        self.on_dtmf = None
        self.on_ctcss = None
        self.sr = 2e6

    def start(self, sample_rate=2e6):
        self.sr = sample_rate
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        try:
            import sounddevice as sd
            self._out = sd.OutputStream(
                samplerate=AUDIO_RATE, channels=1, dtype="float32")
            self._out.start()
        except Exception as e:
            print(f"Audio output unavailable: {e}")

    def feed(self, iq: np.ndarray):
        if self.running:
            try:
                self._q.put_nowait(iq.astype(np.complex64))
            except queue.Full:
                pass

    def stop(self):
        self.running = False
        if self._out:
            try:
                self._out.stop()
                self._out.close()
            except Exception:
                pass

    def _worker(self):
        while self.running:
            try:
                iq = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            audio = self._demod(iq)
            if audio is not None and self._out:
                try:
                    self._out.write(audio * self.volume)
                except Exception:
                    pass

    def _demod(self, iq: np.ndarray):
        pdb = 10 * np.log10(np.mean(np.abs(iq) ** 2) + 1e-12)
        if pdb < self.squelch_db:
            return np.zeros(int(len(iq) * AUDIO_RATE / self.sr), dtype=np.float32)
        dec = max(1, int(self.sr / AUDIO_RATE))
        iqd = sp.decimate(iq, dec, ftype="fir", zero_phase=True) if dec > 1 else iq
        if self.mode == "FM":
            audio = self._fm(iqd)
        elif self.mode == "AM":
            audio = np.abs(iqd).astype(np.float32)
        elif self.mode == "USB":
            audio = self._ssb(iqd, "USB")
        elif self.mode == "LSB":
            audio = self._ssb(iqd, "LSB")
        elif self.mode == "CW":
            audio = self._cw(iqd)
        else:
            audio = np.real(iqd).astype(np.float32)
        mx = np.max(np.abs(audio))
        if mx > 0:
            audio = audio / mx * 0.8
        self._detect_dtmf(audio)
        return audio.astype(np.float32)

    def _fm(self, iq):
        d = np.diff(np.angle(iq))
        return ((d + np.pi) % (2 * np.pi) - np.pi).astype(np.float32)

    def _ssb(self, iq, mode):
        a = sp.hilbert(np.real(iq))
        if mode == "USB":
            return (np.real(a) + np.imag(a)).astype(np.float32)
        return (np.real(a) - np.imag(a)).astype(np.float32)

    def _cw(self, iq):
        env = np.abs(iq)
        t = np.arange(len(env)) / AUDIO_RATE
        return (env * np.sin(2 * np.pi * 700 * t)).astype(np.float32)

    def _detect_dtmf(self, audio):
        if len(audio) < 256:
            return
        freqs = np.fft.rfftfreq(len(audio), 1 / AUDIO_RATE)
        fft = np.abs(np.fft.rfft(audio))

        def pk(f):
            i = np.argmin(np.abs(freqs - f))
            return fft[max(0, i - 3):i + 4].max()

        lf = max([697, 770, 852, 941], key=pk)
        hf = max([1209, 1336, 1477, 1633], key=pk)
        key = DTMF_MAP.get((lf, hf))
        if key and pk(lf) > 0.05:
            if not self.dtmf_buffer or self.dtmf_buffer[-1] != key:
                self.dtmf_buffer.append(key)
                if self.on_dtmf:
                    self.on_dtmf(key)

    def get_ctcss(self, iq) -> float:
        audio = self._fm(iq)
        freqs = np.fft.rfftfreq(len(audio), 1 / AUDIO_RATE)
        fft = np.abs(np.fft.rfft(audio))
        best = max(CTCSS_TONES, key=lambda f: fft[np.argmin(np.abs(freqs - f))])
        if self.on_ctcss:
            self.on_ctcss(best)
        return best
