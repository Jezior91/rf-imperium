"""RF Imperium — RF Fuzzer (systematyczna analiza reakcji)"""
import numpy as np
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class FuzzResult:
    iteration: int
    bits: str
    response: Optional[str]
    hit: bool
    timestamp: float = 0.0


class RFFuzzer:
    def __init__(self):
        self.running = False
        self.results: list[FuzzResult] = []
        self.on_result: Optional[Callable] = None
        self.on_done: Optional[Callable] = None
        self._thread = None

    def _bits_to_iq(self, bits: str, symbol_rate=1000,
                    sample_rate=2e6) -> np.ndarray:
        sps = max(1, int(sample_rate / symbol_rate))
        iq = np.zeros(len(bits) * sps, dtype=np.complex64)
        for i, b in enumerate(bits):
            if b == "1":
                iq[i * sps:(i + 1) * sps] = 1.0 + 0j
        return iq

    def start_bitflip(self, base_bits: str, tx_fn: Callable,
                      response_fn: Optional[Callable] = None,
                      delay=0.1, max_iterations=None, symbol_rate=1000):
        """Przerzuca po 1 bicie i obserwuje reakcję"""
        self.running = True
        self.results = []

        def _run():
            n = len(base_bits)
            iterations = min(max_iterations or n, n)
            for i in range(iterations):
                if not self.running:
                    break
                mutated = list(base_bits)
                mutated[i] = "0" if mutated[i] == "1" else "1"
                bits_str = "".join(mutated)
                iq = self._bits_to_iq(bits_str, symbol_rate)
                tx_fn(iq)
                time.sleep(delay)
                response = response_fn() if response_fn else None
                hit = response is not None and bool(str(response).strip())
                result = FuzzResult(i, bits_str, response, hit,
                                    timestamp=time.time())
                self.results.append(result)
                if self.on_result:
                    self.on_result(result)
            self.running = False
            if self.on_done:
                self.on_done(self.results)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def start_field_increment(self, base_bits: str, field_start: int,
                               field_len: int, tx_fn: Callable,
                               response_fn: Optional[Callable] = None,
                               delay=0.1, symbol_rate=1000):
        """Inkrementuje wartość konkretnego pola ramki"""
        self.running = True
        self.results = []
        max_val = 2 ** field_len

        def _run():
            for val in range(max_val):
                if not self.running:
                    break
                bits = list(base_bits)
                field_bits = format(val, f"0{field_len}b")
                bits[field_start:field_start + field_len] = list(field_bits)
                bits_str = "".join(bits)
                iq = self._bits_to_iq(bits_str, symbol_rate)
                tx_fn(iq)
                time.sleep(delay)
                response = response_fn() if response_fn else None
                hit = response is not None
                result = FuzzResult(val, bits_str, response, hit,
                                    timestamp=time.time())
                self.results.append(result)
                if self.on_result:
                    self.on_result(result)
            self.running = False
            if self.on_done:
                self.on_done(self.results)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def start_random(self, bit_length: int, tx_fn: Callable,
                     response_fn: Optional[Callable] = None,
                     delay=0.1, count=1000, symbol_rate=1000):
        """Losowe ramki"""
        self.running = True
        self.results = []

        def _run():
            for i in range(count):
                if not self.running:
                    break
                bits = "".join(str(b) for b in np.random.randint(0, 2, bit_length))
                iq = self._bits_to_iq(bits, symbol_rate)
                tx_fn(iq)
                time.sleep(delay)
                response = response_fn() if response_fn else None
                hit = response is not None
                result = FuzzResult(i, bits, response, hit,
                                    timestamp=time.time())
                self.results.append(result)
                if self.on_result:
                    self.on_result(result)
            self.running = False
            if self.on_done:
                self.on_done(self.results)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def get_hits(self) -> list:
        return [r for r in self.results if r.hit]

    def get_stats(self) -> dict:
        return {
            "total": len(self.results),
            "hits": len(self.get_hits()),
            "running": self.running,
            "hit_rate": round(len(self.get_hits()) / max(len(self.results), 1), 3),
        }
