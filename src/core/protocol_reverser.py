"""RF Imperium — Auto Protocol Reverser (nieznane protokoły)"""
import numpy as np
from collections import Counter


class ProtocolReverser:
    def __init__(self):
        self.frames = []
        self.analysis = {}

    def add_frame(self, bits: str):
        self.frames.append(bits.strip())

    def clear(self):
        self.frames = []
        self.analysis = {}

    def analyze(self) -> dict:
        if not self.frames:
            return {"error": "Brak ramek — dodaj przynajmniej 2"}
        lengths = [len(f) for f in self.frames]
        dom = Counter(lengths).most_common(1)[0][0]
        frames = [f for f in self.frames if len(f) == dom]

        # Preambuła — stałe bity z przodu
        pre = 0
        for i in range(min(dom, 64)):
            if len(set(f[i] for f in frames)) == 1:
                pre += 1
            else:
                break

        # Fixed vs Variable positions
        fixed = [i for i in range(dom) if len(set(f[i] for f in frames)) == 1]
        variable = [i for i in range(dom) if i not in fixed]

        # Segmentacja zmiennych pól
        segs = []
        in_v = False
        s0 = 0
        for i in range(dom):
            iv = i in variable
            if iv and not in_v:
                s0 = i; in_v = True
            elif not iv and in_v:
                segs.append({"start": s0, "end": i, "len": i - s0})
                in_v = False
        if in_v:
            segs.append({"start": s0, "end": dom, "len": dom - s0})

        for seg in segs:
            vals = ["".join(f[seg["start"]:seg["end"]]) for f in frames]
            cnt = Counter(vals)
            total = len(vals)
            ent = -sum((c / total) * np.log2(c / total + 1e-12) for c in cnt.values())
            seg["entropy"] = round(float(ent), 3)
            seg["unique_values"] = len(cnt)
            seg["examples"] = [v for v, _ in cnt.most_common(5)]

        avg_v = len(variable) / dom if dom else 0
        if avg_v > 0.7:
            mod_guess = "PSK/QAM"
        elif avg_v > 0.3:
            mod_guess = "FSK/ASK"
        else:
            mod_guess = "OOK/ASK"

        frames_hex = []
        for f in frames[:10]:
            try:
                frames_hex.append(hex(int(f, 2))[2:].upper().zfill(dom // 4))
            except Exception:
                pass

        result = {
            "frame_count": len(frames),
            "dominant_length": dom,
            "preamble_bits": pre,
            "preamble_value": frames[0][:pre] if pre else "",
            "fixed_bits": len(fixed),
            "variable_bits": len(variable),
            "segments": segs,
            "possible_crc8": 1 < len(set(f[-8:] for f in frames)) < len(frames),
            "possible_crc16": 1 < len(set(f[-16:] for f in frames)) < len(frames),
            "modulation_guess": mod_guess,
            "frames_hex": frames_hex,
        }
        self.analysis = result
        return result

    def suggest_fields(self) -> list:
        if not self.analysis:
            self.analyze()
        segs = self.analysis.get("segments", [])
        out = []
        for i, seg in enumerate(segs):
            n = seg["len"]
            ent = seg.get("entropy", 0)
            uniq = seg.get("unique_values", 0)
            if i == 0 and ent < 0.5:
                name = "DEVICE_ID"
            elif i == len(segs) - 1 and n in (8, 16):
                name = "CRC"
            elif n == 8 and ent > 2:
                name = "PAYLOAD"
            elif n <= 4 and uniq <= 4:
                name = f"CMD_{i}"
            elif n == 8 and uniq <= 8:
                name = "CHANNEL"
            else:
                name = f"FIELD_{i}_b{n}"
            out.append({"field": name, **seg})
        return out

    def to_c_struct(self) -> str:
        fields = self.suggest_fields()
        dom = self.analysis.get("dominant_length", 0)
        lines = [
            f"/* RF Imperium Auto-Reversed Frame ({dom} bits) */",
            "typedef struct {",
        ]
        for f in fields:
            bits = f["len"]
            t = "uint8_t" if bits <= 8 else "uint16_t" if bits <= 16 else "uint32_t"
            lines.append(f"    {t} {f['field'].lower()}; /* {bits} bits */")
        lines.append("} rf_frame_t;")
        return "\n".join(lines)

    def generate_dissector_py(self) -> str:
        """Generuje Python dissector dla wykrytego protokołu"""
        fields = self.suggest_fields()
        dom = self.analysis.get("dominant_length", 0)
        lines = [
            "def dissect(bits: str) -> dict:",
            f'    """Auto-generated dissector for {dom}-bit frame"""',
            "    if len(bits) < " + str(dom) + ":",
            '        return {"error": "Frame too short"}',
            "    return {",
        ]
        for f in fields:
            lines.append(f"        '{f['field'].lower()}': int(bits[{f['start']}:{f['end']}], 2),")
        lines.append("    }")
        return "\n".join(lines)
