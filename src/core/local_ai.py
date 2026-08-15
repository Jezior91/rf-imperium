"""RF Imperium — Local AI Classifier (scikit-learn, offline)"""
import numpy as np
import json
import pickle
from pathlib import Path

MODEL_FILE = Path.home() / ".rf_imperium" / "local_model.pkl"
LABELS_FILE = Path.home() / ".rf_imperium" / "local_labels.json"
TRAINING_FILE = Path.home() / ".rf_imperium" / "training_data.json"


class LocalAIClassifier:
    def __init__(self):
        self.model = None
        self.labels: list[str] = []
        self.feature_names: list[str] = []
        self._load()

    def _load(self):
        if MODEL_FILE.exists():
            try:
                with open(MODEL_FILE, "rb") as f:
                    self.model = pickle.load(f)
            except Exception:
                pass
        if LABELS_FILE.exists():
            try:
                data = json.loads(LABELS_FILE.read_text())
                self.labels = data.get("labels", [])
                self.feature_names = data.get("features", [])
            except Exception:
                pass

    def _save(self):
        MODEL_FILE.parent.mkdir(exist_ok=True)
        with open(MODEL_FILE, "wb") as f:
            pickle.dump(self.model, f)
        LABELS_FILE.write_text(json.dumps({
            "labels": self.labels,
            "features": self.feature_names,
        }, indent=2))

    def extract_features(self, iq: np.ndarray) -> np.ndarray:
        """128 FFT bins + 32 envelope bins + 32 phase-diff bins = 192 features"""
        n = 4096
        if len(iq) < n:
            iq = np.pad(iq, (0, n - len(iq)))
        iq = iq[:n]

        # FFT magnitude (128 bins normalized)
        fft = np.abs(np.fft.fft(iq, n=256))[:128]
        mx = fft.max()
        fft_n = fft / (mx + 1e-12)

        # Envelope (decimated to 32)
        env = np.abs(iq)
        step = n // 32
        env_d = np.array([env[i * step:(i + 1) * step].mean()
                          for i in range(32)], dtype=np.float32)
        emx = env_d.max()
        env_d = env_d / (emx + 1e-12)

        # Phase difference (decimated to 32)
        phase = np.angle(iq)
        phase_d = np.diff(phase, prepend=0)
        step2 = n // 32
        ph_d = np.array([phase_d[i * step2:(i + 1) * step2].mean()
                         for i in range(32)], dtype=np.float32)

        return np.concatenate([fft_n, env_d, ph_d]).astype(np.float32)

    def train(self, iq_samples: list, labels: list) -> bool:
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.preprocessing import LabelEncoder
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            return False

        X = np.array([self.extract_features(iq) for iq in iq_samples])
        le = LabelEncoder()
        y = le.fit_transform(labels)
        self.labels = list(le.classes_)

        self.model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200, max_depth=15,
                random_state=42, n_jobs=-1,
            )),
        ])
        self.model.fit(X, y)
        self._save()
        return True

    def predict(self, iq: np.ndarray) -> dict:
        if self.model is None:
            return {
                "protocol": "Unknown (model nie załadowany)",
                "confidence": 0.0,
                "probabilities": {},
            }
        feat = self.extract_features(iq).reshape(1, -1)
        try:
            proba = self.model.predict_proba(feat)[0]
            idx = int(np.argmax(proba))
            label = self.labels[idx] if idx < len(self.labels) else "Unknown"
            prob_dict = {
                self.labels[i]: round(float(p), 3)
                for i, p in enumerate(proba)
                if i < len(self.labels)
            }
            return {
                "protocol": label,
                "confidence": round(float(proba[idx]), 3),
                "probabilities": prob_dict,
            }
        except Exception as e:
            return {"protocol": f"Predict ERR: {e}", "confidence": 0.0, "probabilities": {}}

    def add_training_sample(self, iq: np.ndarray, label: str):
        """Dodaj próbkę do bazy treningowej (do późniejszego treningu)"""
        TRAINING_FILE.parent.mkdir(exist_ok=True)
        data = []
        if TRAINING_FILE.exists():
            try:
                data = json.loads(TRAINING_FILE.read_text())
            except Exception:
                pass
        feat = self.extract_features(iq).tolist()
        data.append({"label": label, "features": feat})
        TRAINING_FILE.write_text(json.dumps(data))

    def train_from_saved(self) -> bool:
        if not TRAINING_FILE.exists():
            return False
        try:
            data = json.loads(TRAINING_FILE.read_text())
            labels = [d["label"] for d in data]
            # Odtwórz IQ z features (uproszczone — trenuj na gotowych cechach)
            X = np.array([d["features"] for d in data], dtype=np.float32)
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y = le.fit_transform(labels)
            self.labels = list(le.classes_)
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model.fit(X, y)
            self._save()
            return True
        except Exception:
            return False

    def is_trained(self) -> bool:
        return self.model is not None

    def label_count(self) -> int:
        return len(self.labels)
