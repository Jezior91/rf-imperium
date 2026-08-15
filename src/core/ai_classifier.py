"""RF Imperium — AI Classifier (OpenAI GPT — opcjonalny)"""
import json


class AIClassifier:
    def __init__(self, api_key="", model="gpt-4o"):
        self.api_key=api_key; self.model=model
        self.enabled=bool(api_key); self.last_result={}; self.call_count=0

    def classify(self, freq_hz, power_dbm, protocol, bits="", decoded="", extra_ctx=""):
        if not self.enabled:
            return {"classification":"AI offline (brak klucza API)","threat_level":0,
                    "confidence":0.0,"device_type":"unknown",
                    "recommendation":"Skonfiguruj OpenAI API key w ustawieniach"}
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            prompt = (f"RF signal analysis:\nFrequency: {freq_hz/1e6:.4f} MHz\n"
                      f"Power: {power_dbm:.1f} dBm\nProtocol: {protocol}\n"
                      f"Decoded: {decoded[:100]}\nBits: {bits[:64]}\n{extra_ctx}\n\n"
                      "Respond ONLY with JSON: classification, device_type, "
                      "threat_level(0-10), confidence(0-1), recommendation, notes")
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":"You are an RF security expert. JSON only."},
                          {"role":"user","content":prompt}],
                max_tokens=400, response_format={"type":"json_object"})
            self.last_result = json.loads(resp.choices[0].message.content)
            self.call_count += 1; return self.last_result
        except Exception as e:
            return {"classification":f"AI ERR: {e}","threat_level":0,"confidence":0.0,
                    "device_type":"unknown","recommendation":str(e)}

    def update_key(self, api_key, model="gpt-4o"):
        self.api_key=api_key; self.model=model; self.enabled=bool(api_key)
