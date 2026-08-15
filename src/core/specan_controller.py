"""RF Imperium — Spectrum Analyzer + Signal Generator (SCPI/VISA)"""
import threading, time, numpy as np
try:
    import pyvisa as visa; VISA_OK = True
except ImportError:
    VISA_OK = False


class SpecAnController:
    def __init__(self, sa_resource="", sg_resource="", timeout=5000):
        self.sa_resource=sa_resource; self.sg_resource=sg_resource
        self.timeout=timeout; self.rm=None
        self.sa_inst=None; self.sg_inst=None
        self.sa_connected=False; self.sg_connected=False
        self.on_status=None; self.on_trace=None

    def connect_sa(self):
        if not VISA_OK:
            if self.on_status: self.on_status("PyVISA nie zainstalowany")
            return False
        try:
            if not self.rm: self.rm = visa.ResourceManager()
            self.sa_inst = self.rm.open_resource(self.sa_resource)
            self.sa_inst.timeout = self.timeout
            idn = self.sa_inst.query("*IDN?").strip()
            self.sa_connected = True
            if self.on_status: self.on_status(f"SpecAn: {idn}")
            return True
        except Exception as e:
            if self.on_status: self.on_status(f"SpecAn ERR: {e}")
            return False

    def connect_sg(self):
        if not VISA_OK: return False
        try:
            if not self.rm: self.rm = visa.ResourceManager()
            self.sg_inst = self.rm.open_resource(self.sg_resource)
            self.sg_inst.timeout = self.timeout
            idn = self.sg_inst.query("*IDN?").strip()
            self.sg_connected = True
            if self.on_status: self.on_status(f"SigGen: {idn}")
            return True
        except Exception as e:
            if self.on_status: self.on_status(f"SigGen ERR: {e}")
            return False

    def sa_write(self, cmd):
        if self.sa_inst: self.sa_inst.write(cmd)
    def sa_query(self, cmd):
        return self.sa_inst.query(cmd) if self.sa_inst else ""
    def sa_set_center(self, hz): self.sa_write(f":SENS:FREQ:CENT {hz}")
    def sa_set_span(self, hz): self.sa_write(f":SENS:FREQ:SPAN {hz}")
    def sa_set_rbw(self, hz): self.sa_write(f":SENS:BWID {hz}")
    def sa_set_ref_level(self, dbm): self.sa_write(f":DISP:WIND:TRAC:Y:RLEV {dbm}")
    def sa_set_atten(self, db): self.sa_write(f":SENS:POW:ATT {db}")

    def sa_fetch_trace(self):
        if not self.sa_connected: return None,None
        try:
            raw = self.sa_query(":TRAC:DATA? TRACE1")
            vals = [float(x) for x in raw.strip().split(",")]
            start = float(self.sa_query(":SENS:FREQ:STAR?"))
            stop = float(self.sa_query(":SENS:FREQ:STOP?"))
            return np.linspace(start,stop,len(vals)), np.array(vals,dtype=np.float32)
        except Exception as e:
            if self.on_status: self.on_status(f"Trace ERR: {e}")
            return None,None

    def sa_marker_peak(self):
        self.sa_write(":CALC:MARK1:MAX")
        try:
            return {"freq_hz":float(self.sa_query(":CALC:MARK1:X?")),
                    "power_dbm":float(self.sa_query(":CALC:MARK1:Y?"))}
        except: return {}

    def start_continuous(self, interval=0.5):
        def _loop():
            while self.sa_connected:
                f,d = self.sa_fetch_trace()
                if f is not None and self.on_trace: self.on_trace(f,d)
                time.sleep(interval)
        threading.Thread(target=_loop,daemon=True).start()

    def sg_write(self, cmd):
        if self.sg_inst: self.sg_inst.write(cmd)
    def sg_query(self, cmd): return self.sg_inst.query(cmd) if self.sg_inst else ""
    def sg_set_freq(self, hz): self.sg_write(f":SOUR:FREQ {hz}")
    def sg_set_power(self, dbm): self.sg_write(f":SOUR:POW:LEV:IMM:AMPL {dbm}dBm")
    def sg_set_output(self, on): self.sg_write(f":OUTP:STAT {'ON' if on else 'OFF'}")
    def sg_cw(self, hz, dbm=-10):
        self.sg_set_freq(hz); self.sg_set_power(dbm)
        self.sg_write(":SOUR:MOD:STAT OFF"); self.sg_set_output(True)
    def sg_off(self): self.sg_set_output(False)

    def list_resources(self):
        if not VISA_OK: return []
        try:
            if not self.rm: self.rm = visa.ResourceManager()
            return list(self.rm.list_resources())
        except: return []

    def disconnect(self):
        self.sa_connected=False; self.sg_connected=False
        for inst in [self.sa_inst, self.sg_inst]:
            if inst:
                try: inst.close()
                except: pass
