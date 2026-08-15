"""RF Imperium — Sweep Engine (1Hz–6GHz)"""
import numpy as np, threading, time, csv


class SweepEngine:
    def __init__(self, hackrf):
        self.hackrf=hackrf; self.running=False; self._thread=None
        self.on_peak=None; self.on_progress=None; self.on_done=None
        self.results={}; self.peak_map={}

    def start(self, start_hz, stop_hz, step_hz, dwell_ms=100, threshold_dbm=-80.0):
        self.running=True; self.results={}
        self._thread=threading.Thread(
            target=self._sweep,args=(start_hz,stop_hz,step_hz,dwell_ms,threshold_dbm),daemon=True)
        self._thread.start()

    def _sweep(self, start_hz, stop_hz, step_hz, dwell_ms, threshold_dbm):
        freqs = np.arange(start_hz, stop_hz+step_hz, step_hz)
        total = len(freqs)
        for i,freq in enumerate(freqs):
            if not self.running: break
            self.hackrf.set_freq(freq)
            time.sleep(dwell_ms/1000.0)
            if self.hackrf._last_fft is not None:
                pwr = float(np.max(self.hackrf._last_fft))
                self.results[float(freq)] = pwr
                self.peak_map[float(freq)] = max(self.peak_map.get(float(freq),-200.0),pwr)
                if pwr>threshold_dbm and self.on_peak: self.on_peak(freq,pwr)
            else:
                self.results[float(freq)] = -100.0
            if self.on_progress: self.on_progress(i+1,total,freq)
        self.running=False
        if self.on_done: self.on_done(self.results)

    def stop(self):
        self.running=False
        if self._thread: self._thread.join(timeout=3)

    def get_sorted_peaks(self, threshold_dbm=-80.0):
        return sorted([{"freq_hz":f,"freq_mhz":round(f/1e6,4),"power_dbm":p}
                        for f,p in self.results.items() if p>=threshold_dbm],
                      key=lambda x: -x["power_dbm"])

    def export_csv(self, path):
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["freq_hz","freq_mhz","power_dbm"])
            for freq,pwr in sorted(self.results.items()):
                w.writerow([freq,round(freq/1e6,6),round(pwr,2)])
