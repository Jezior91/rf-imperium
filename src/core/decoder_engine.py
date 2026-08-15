"""RF Imperium — Decoder Engine (OOK/ASK/FSK/APRS/AIS/RDS/POCSAG)"""
import numpy as np
from scipy import signal as sp
from dataclasses import dataclass, field


@dataclass
class DecodedFrame:
    protocol: str; freq_hz: float; power_dbm: float
    bits: str = ""; hex_data: str = ""; decoded: str = ""
    raw_bytes: bytes = b""; extra: dict = field(default_factory=dict)
    def short(self): return f"{self.protocol}@{self.freq_hz/1e6:.4f}MHz {self.power_dbm:.1f}dBm {self.decoded[:60]}"


class DecoderEngine:
    def __init__(self):
        self.on_frame = None; self.min_power_dbm = -90.0

    def process(self, iq, sample_rate, center_freq) -> list:
        pwr = 10*np.log10(np.mean(np.abs(iq)**2)+1e-12)
        if pwr < self.min_power_dbm: return []
        results = (self._ook_ask(iq,sample_rate,center_freq,pwr) +
                   self._fsk(iq,sample_rate,center_freq,pwr) +
                   self._aprs(iq,sample_rate,center_freq,pwr) +
                   self._ais(iq,sample_rate,center_freq,pwr) +
                   self._rds(iq,sample_rate,center_freq,pwr) +
                   self._pocsag(iq,sample_rate,center_freq,pwr))
        for r in results:
            if self.on_frame: self.on_frame(r)
        return results

    def _ook_ask(self, iq, sr, cf, pwr):
        env = np.abs(iq); thr = (env.max()+env.min())/2
        bits_raw = (env>thr).astype(np.int8)
        if len(np.where(np.diff(bits_raw)!=0)[0]) < 6: return []
        sd = self._est_sym(bits_raw); 
        if sd<=0: return []
        bits = self._sample_bits(bits_raw, sd)
        if len(bits)<8: return []
        bs = "".join(str(b) for b in bits)
        proto, dec = self._classify_ook(bs, cf)
        hx = ""
        try: hx = hex(int(bs,2))[2:].upper().zfill(len(bs)//4) if len(bs)>=4 else ""
        except: pass
        return [DecodedFrame(proto,cf,pwr,bs,hx,dec)]

    def _classify_ook(self, bits, cf):
        mhz = cf/1e6
        if 433.6<=mhz<=434.1:
            if len(bits)==24: return "EV1527",f"Addr={bits[:20]} Data={bits[20:]}"
            if len(bits)==25: return "PT2262","Tristate frame"
            return "433MHz-OOK",bits[:48]
        elif 867<=mhz<=869.5: return "868MHz-OOK",bits[:48]
        elif 314.5<=mhz<=315.5: return "315MHz-OOK",bits[:48]
        elif 2400<=mhz<=2500: return "2.4GHz-OOK",bits[:48]
        return "OOK",bits[:64]

    def _fsk(self, iq, sr, cf, pwr):
        if len(iq)<512: return []
        fm = np.diff(np.unwrap(np.angle(iq)))
        bits_raw = (fm>np.median(fm)).astype(np.int8)
        sd = self._est_sym(bits_raw)
        if sd<=0: return []
        bits = self._sample_bits(bits_raw, sd)
        if len(bits)<8: return []
        bs = "".join(str(b) for b in bits); nrzi = self._nrzi(bs)
        mhz = cf/1e6
        if 143<=mhz<=146: proto="APRS-FSK"
        elif 160<=mhz<=163: proto="AIS-FSK"
        else: proto="FSK"
        hx = ""
        try: hx = hex(int(bs,2))[2:].upper().zfill(len(bs)//4) if len(bs)>=4 else ""
        except: pass
        return [DecodedFrame(proto,cf,pwr,bs,hx,nrzi[:64])]

    def _aprs(self, iq, sr, cf, pwr):
        mhz = cf/1e6
        if not (143.5<=mhz<=145.5): return []
        fm = np.diff(np.unwrap(np.angle(iq)))
        b1 = self._bpf(fm,1000,1400,sr); b2 = self._bpf(fm,2000,2400,sr)
        if np.mean(b1**2)<0.005 and np.mean(b2**2)<0.005: return []
        return [DecodedFrame("APRS",cf,pwr,decoded=f"APRS {cf/1e6:.3f}MHz AFSK1200")]

    def _ais(self, iq, sr, cf, pwr):
        mhz = cf/1e6
        if not (161.9<=mhz<=162.1): return []
        fm = np.diff(np.unwrap(np.angle(iq)))
        if np.var(fm)>0.01:
            return [DecodedFrame("AIS",cf,pwr,decoded=f"AIS vessel {cf/1e6:.3f}MHz GMSK")]
        return []

    def _rds(self, iq, sr, cf, pwr):
        mhz = cf/1e6
        if not (87.5<=mhz<=108.0) or sr<200e3: return []
        return [DecodedFrame("RDS/FM",cf,pwr,decoded=f"FM+RDS {cf/1e6:.2f}MHz")]

    def _pocsag(self, iq, sr, cf, pwr):
        mhz = cf/1e6
        if not (138<=mhz<=175 or 400<=mhz<=470): return []
        fm = np.diff(np.unwrap(np.angle(iq)))
        if np.var(fm)>0.02:
            return [DecodedFrame("POCSAG",cf,pwr,decoded=f"Pager POCSAG {cf/1e6:.4f}MHz")]
        return []

    def _est_sym(self, bits):
        edges = np.where(np.diff(bits.astype(np.int8))!=0)[0]
        if len(edges)<4: return 0
        gaps = np.diff(edges)
        return max(int(np.min(gaps)),1) if len(gaps) else 0

    def _sample_bits(self, bits_raw, sd):
        out=[]; i=0
        while i+sd<=len(bits_raw) and len(out)<256:
            out.append(1 if np.mean(bits_raw[i:i+sd])>0.5 else 0); i+=sd
        return out

    def _nrzi(self, bits):
        if not bits: return ""
        out=[bits[0]]
        for i in range(1,len(bits)): out.append("0" if bits[i]==bits[i-1] else "1")
        return "".join(out)

    def _bpf(self, sig, fl, fh, sr):
        nyq=sr/2; lo,hi=fl/nyq,fh/nyq
        if lo<=0 or hi>=1 or lo>=hi: return sig
        try:
            b,a=sp.butter(4,[lo,hi],btype="band"); return sp.lfilter(b,a,sig)
        except: return sig
