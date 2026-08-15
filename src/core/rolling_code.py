"""RF Imperium — Rolling Code Analyzer (KeeLoq, HCS301, PT2262, EV1527)"""
import numpy as np
from collections import Counter
from typing import Optional


class RollingCodeAnalyzer:
    KEELOQ_NLF = 0x3A5C742E

    def __init__(self):
        self.captured: list[str] = []
        self.predicted: list[str] = []
        self.on_code = None

    def add_code(self, bits: str):
        self.captured.append(bits.strip())
        if self.on_code:
            self.on_code(bits.strip())

    def clear(self):
        self.captured = []
        self.predicted = []

    # ── KeeLoq ───────────────────────────────────────────────────
    def _keeloq_nlf(self, x: int) -> int:
        return (self.KEELOQ_NLF >> (x & 0x1F)) & 1

    def _keeloq_decrypt(self, data: int, key: int) -> int:
        for _ in range(528):
            bit = (
                ((data >> 31) ^ (data >> 15) ^ (data >> 8) ^
                 (data >> 4) ^ (data >> 2) ^ (data >> 1) ^ data ^
                 (key & 1) ^ self._keeloq_nlf(
                    (data & 0xF) | ((data >> 24) & 0x10))) & 1
            )
            data = ((data >> 1) | (bit << 31)) & 0xFFFFFFFF
            key = ((key >> 1) | ((key & 1) << 63)) & 0xFFFFFFFFFFFFFFFF
        return data

    def _keeloq_encrypt(self, data: int, key: int) -> int:
        for _ in range(528):
            bit = (
                ((data >> 28) ^ (data >> 19) ^ (data >> 9) ^
                 (data >> 7) ^ data ^ (key >> 63) ^
                 self._keeloq_nlf((data >> 28) & 0xF | ((data >> 23) & 0x10))) & 1
            )
            data = ((data << 1) & 0xFFFFFFFF) | bit
            key = ((key << 1) & 0xFFFFFFFFFFFFFFFF) | ((key >> 63) & 1)
        return data

    # ── Analiza sekwencji ─────────────────────────────────────────
    def analyze(self) -> dict:
        if len(self.captured) < 2:
            return {"error": "Potrzeba min. 2 kodów"}

        lengths = [len(c) for c in self.captured]
        dom_len = Counter(lengths).most_common(1)[0][0]
        codes_hex = []
        for c in self.captured[:20]:
            try:
                codes_hex.append(hex(int(c, 2))[2:].upper().zfill(len(c) // 4))
            except Exception:
                pass

        # Wykrywanie protokołu
        if dom_len in (64, 66):
            protocol = "KeeLoq/HCS301"
        elif dom_len == 24:
            protocol = "PT2262/EV1527"
        elif dom_len == 25:
            protocol = "EV1527"
        elif dom_len == 12:
            protocol = "PT2260"
        else:
            protocol = f"Nieznany ({dom_len}b)"

        # Analiza przyrostów licznika
        diffs = []
        for i in range(1, len(self.captured)):
            try:
                v1 = int(self.captured[i - 1], 2)
                v2 = int(self.captured[i], 2)
                diffs.append(v2 - v1)
            except Exception:
                pass

        prediction = "Brak danych"
        counter_step = None
        if diffs:
            if len(set(diffs)) == 1:
                prediction = f"Liniowy (step={diffs[0]}) — przewidywalny"
                counter_step = diffs[0]
            elif len(set(diffs)) <= 3:
                prediction = "Quasi-liniowy — może być przewidywalny"
            else:
                prediction = "Nieliniowy — prawdopodobnie szyfrowany (KeeLoq)"

        return {
            "code_count": len(self.captured),
            "dominant_length": dom_len,
            "protocol": protocol,
            "codes_hex": codes_hex,
            "counter_increments": diffs[:20],
            "counter_step": counter_step,
            "prediction": prediction,
        }

    def predict_next(self, count=5) -> list[str]:
        if len(self.captured) < 2:
            return []
        try:
            last = int(self.captured[-1], 2)
            prev = int(self.captured[-2], 2)
            step = last - prev
            length = len(self.captured[-1])
            mask = 2 ** length - 1
            preds = []
            v = last
            for _ in range(count):
                v = (v + step) & mask
                preds.append(format(v, f"0{length}b"))
            self.predicted = preds
            return preds
        except Exception:
            return []

    def pt2262_decode(self, bits: str) -> dict:
        """Dekoduj PT2262/EV1527 (tristate encoding)"""
        tri_map = {"10": "0", "01": "F", "11": "1", "00": "?"}
        if len(bits) < 24:
            return {"error": "Za krótka ramka"}
        addr_bits = bits[:20]
        data_bits = bits[20:24]
        addr_tri = "".join(
            tri_map.get(addr_bits[i * 2:i * 2 + 2], "?") for i in range(10)
        )
        return {
            "raw_bits": bits,
            "address_tristate": addr_tri,
            "data_nibble_bin": data_bits,
            "data_hex": hex(int(data_bits, 2))[2:].upper(),
            "protocol": "PT2262/EV1527",
        }
