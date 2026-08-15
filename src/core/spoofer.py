"""RF Imperium — Spoofer / Replay / Substitute / Jam Engine"""
import numpy as np, threading, time


class Spoofer:
    def __init__(self):
        self.on_status = None; self._thread = None; self.running = False

    def _ook(self, bits, symbol_rate, sample_rate):
        sps = max(1, int(sample_rate/symbol_rate))
        iq = np.zeros(len(bits)*sps, dtype=np.complex64)
        for i,b in enumerate(bits):
            if b=="1": iq[i*sps:(i+1)*sps] = 1.0+0j
        ramp = min(sps//4, 16)
        if ramp>0:
            iq[:ramp] *= np.linspace(0,1,ramp)
            iq[-ramp:] *= np.linspace(1,0,ramp)
        return iq

    def _fsk(self, bits, f_mark, f_space, symbol_rate, sample_rate):
        sps = max(1, int(sample_rate/symbol_rate))
        iq = np.zeros(len(bits)*sps, dtype=np.complex64)
        for i,b in enumerate(bits):
            t = np.arange(sps)/sample_rate
            f = f_mark if b=="1" else f_space
            iq[i*sps:(i+1)*sps] = np.exp(2j*np.pi*f*t)
        return iq

    def replay(self, iq, tx_fn, repeat=1, delay_s=0.5):
        def _send():
            for r in range(repeat):
                if not self.running: break
                tx_fn(iq)
                if self.on_status: self.on_status(f"Replay {r+1}/{repeat}")
                time.sleep(delay_s)
            if self.on_status: self.on_status(f"Replay done ({repeat}x)")
        self.running = True
        self._thread = threading.Thread(target=_send, daemon=True)
        self._thread.start()

    def send_ook(self, bits, freq_hz, symbol_rate, tx_set_freq_fn, tx_fn,
                 sample_rate=2e6, repeat=3, delay_s=0.1):
        if self.on_status: self.on_status(f"TX OOK {freq_hz/1e6:.3f}MHz")
        tx_set_freq_fn(freq_hz)
        iq = self._ook(bits, symbol_rate, sample_rate)
        self.replay(iq, tx_fn, repeat=repeat, delay_s=delay_s)

    def send_fsk(self, bits, freq_hz, f_mark, f_space, symbol_rate,
                 tx_set_freq_fn, tx_fn, sample_rate=2e6):
        if self.on_status: self.on_status(f"TX FSK {freq_hz/1e6:.3f}MHz")
        tx_set_freq_fn(freq_hz)
        iq = self._fsk(bits, f_mark, f_space, symbol_rate, sample_rate)
        self.running = True
        threading.Thread(target=lambda: tx_fn(iq), daemon=True).start()

    def substitute(self, original_iq, new_bits, symbol_rate, tx_fn, sample_rate=2e6):
        new_iq = self._ook(new_bits, symbol_rate, sample_rate)
        n = len(original_iq)
        if len(new_iq)>n: new_iq=new_iq[:n]
        else: new_iq=np.pad(new_iq,(0,n-len(new_iq)))
        self.replay(new_iq, tx_fn, repeat=1)

    def bruteforce_ook(self, freq_hz, bit_length, symbol_rate, tx_set_freq_fn, tx_fn,
                       on_sent=None, sample_rate=2e6, delay=0.05, max_codes=1024):
        tx_set_freq_fn(freq_hz); self.running = True
        def _bf():
            total = min(2**bit_length, max_codes)
            for i in range(total):
                if not self.running: break
                bits = format(i,f"0{bit_length}b")
                tx_fn(self._ook(bits, symbol_rate, sample_rate))
                if on_sent: on_sent(i, bits)
                time.sleep(delay)
            if self.on_status: self.on_status(f"Bruteforce done ({total} kodów)")
            self.running = False
        self._thread = threading.Thread(target=_bf, daemon=True)
        self._thread.start()

    def stop(self): self.running = False
