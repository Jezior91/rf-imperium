"""RF Imperium — HackRF One/Two Controller (SoapySDR + DEMO mode)"""
import numpy as np, threading, time

DEMO_MODE = False
try:
    import SoapySDR
    from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_TX, SOAPY_SDR_CF32
except ImportError:
    DEMO_MODE = True


class HackRFController:
    def __init__(self, cfg: dict):
        self.cfg = cfg; self.sdr = None
        self.rxStream = None; self.txStream = None
        self.running = False; self._rx_thread = None
        self.on_iq = None; self.on_status = None
        self.demo = DEMO_MODE; self.connected = False
        self._demo_phase = 0.0; self._last_fft = None
        self._demo_signals = [(433.92e6,0.6),(868.35e6,0.4),(315.0e6,0.3),(2400e6,0.5)]

    def connect(self) -> bool:
        if self.demo:
            self.connected = True
            if self.on_status: self.on_status("HackRF: DEMO MODE")
            return True
        try:
            results = SoapySDR.Device.enumerate("driver=hackrf")
            if not results: raise RuntimeError("HackRF nie znaleziono")
            idx = min(self.cfg.get("device_index",0), len(results)-1)
            self.sdr = SoapySDR.Device(results[idx])
            self.sdr.setSampleRate(SOAPY_SDR_RX,0,self.cfg["sample_rate"])
            self.sdr.setFrequency(SOAPY_SDR_RX,0,self.cfg["center_freq"])
            self.sdr.setGain(SOAPY_SDR_RX,0,"LNA",self.cfg["lna_gain"])
            self.sdr.setGain(SOAPY_SDR_RX,0,"VGA",self.cfg["vga_gain"])
            self.rxStream = self.sdr.setupStream(SOAPY_SDR_RX,SOAPY_SDR_CF32)
            self.connected = True
            if self.on_status: self.on_status("HackRF: Połączono")
            return True
        except Exception as e:
            if self.on_status: self.on_status(f"HackRF ERR: {e} — DEMO")
            self.demo = True; self.connected = True; return False

    def set_freq(self, hz):
        self.cfg["center_freq"] = hz
        if not self.demo and self.sdr:
            try: self.sdr.setFrequency(SOAPY_SDR_RX,0,hz)
            except: pass

    def set_freq_tx(self, hz):
        if not self.demo and self.sdr:
            try: self.sdr.setFrequency(SOAPY_SDR_TX,0,hz)
            except: pass

    def set_sample_rate(self, r):
        self.cfg["sample_rate"] = r
        if not self.demo and self.sdr:
            try: self.sdr.setSampleRate(SOAPY_SDR_RX,0,r)
            except: pass

    def set_gain(self, lna=None, vga=None):
        if lna is not None: self.cfg["lna_gain"] = lna
        if vga is not None: self.cfg["vga_gain"] = vga
        if not self.demo and self.sdr:
            try:
                if lna: self.sdr.setGain(SOAPY_SDR_RX,0,"LNA",lna)
                if vga: self.sdr.setGain(SOAPY_SDR_RX,0,"VGA",vga)
            except: pass

    def start_rx(self, chunk_size=65536):
        if not self.connected: self.connect()
        self.running = True
        self._rx_thread = threading.Thread(target=self._rx_loop,args=(chunk_size,),daemon=True)
        self._rx_thread.start()

    def _rx_loop(self, chunk_size):
        if self.demo: self._demo_rx(chunk_size); return
        try:
            self.sdr.activateStream(self.rxStream)
            buf = np.zeros(chunk_size, dtype=np.complex64)
            while self.running:
                sr = self.sdr.readStream(self.rxStream,[buf],chunk_size,timeoutUs=1000000)
                if sr.ret>0 and self.on_iq:
                    chunk = buf[:sr.ret].copy()
                    fft = np.abs(np.fft.fft(chunk[:min(len(chunk),1024)]))
                    self._last_fft = 20*np.log10(fft/1024+1e-12)
                    self.on_iq(chunk)
        except Exception as e:
            if self.on_status: self.on_status(f"RX ERR: {e}")
        finally:
            try: self.sdr.deactivateStream(self.rxStream)
            except: pass

    def _demo_rx(self, chunk_size):
        sr = self.cfg.get("sample_rate",2e6)
        while self.running:
            t = np.arange(chunk_size)/sr
            cf = self.cfg.get("center_freq",0)
            iq = np.zeros(chunk_size,dtype=np.complex64)
            for freq,amp in self._demo_signals:
                df = freq-cf
                if abs(df)<sr/2:
                    iq += amp*np.exp(2j*np.pi*df*t+1j*self._demo_phase)
            iq += (np.random.randn(chunk_size)+1j*np.random.randn(chunk_size)).astype(np.complex64)*0.02
            self._demo_phase += 0.15
            fft = np.abs(np.fft.fft(iq[:1024]))
            self._last_fft = 20*np.log10(fft/1024+1e-12)
            if self.on_iq: self.on_iq(iq)
            time.sleep(chunk_size/sr)

    def transmit(self, iq: np.ndarray) -> bool:
        if not self.cfg.get("tx_enabled",False):
            if self.on_status: self.on_status("TX zablokowany — włącz w ustawieniach")
            return False
        if self.demo:
            if self.on_status: self.on_status(f"TX DEMO: {len(iq)} próbek")
            return True
        try:
            if not self.txStream:
                self.sdr.setSampleRate(SOAPY_SDR_TX,0,self.cfg["sample_rate"])
                self.sdr.setFrequency(SOAPY_SDR_TX,0,self.cfg["center_freq"])
                self.sdr.setGain(SOAPY_SDR_TX,0,"VGA",self.cfg.get("tx_gain",20))
                self.txStream = self.sdr.setupStream(SOAPY_SDR_TX,SOAPY_SDR_CF32)
            self.sdr.activateStream(self.txStream)
            sent=0; chunk=131072; iq_cf=iq.astype(np.complex64)
            while sent<len(iq_cf):
                batch=iq_cf[sent:sent+chunk]
                r=self.sdr.writeStream(self.txStream,[batch],len(batch),timeoutUs=1000000)
                if r.ret<0: break
                sent+=r.ret
            self.sdr.deactivateStream(self.txStream)
            return True
        except Exception as e:
            if self.on_status: self.on_status(f"TX ERR: {e}")
            return False

    def stop(self):
        self.running = False
        if self._rx_thread: self._rx_thread.join(timeout=3)
        if not self.demo and self.sdr:
            try: self.sdr.close()
            except: pass
        self.connected = False

    def get_info(self) -> dict:
        return {"mode":"DEMO" if self.demo else "HackRF",
                "freq_hz":self.cfg.get("center_freq",0),
                "sample_rate":self.cfg.get("sample_rate",0),
                "lna_gain":self.cfg.get("lna_gain",0),
                "vga_gain":self.cfg.get("vga_gain",0),
                "tx_enabled":self.cfg.get("tx_enabled",False),
                "connected":self.connected}
