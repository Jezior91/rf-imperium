# RF Imperium v5.0 MAX 🛰️

**Panel kontrolny HackRF One/Two — Windows + Demo przeglądarkowe**

## Zakres: 1 Hz – 6 GHz

---

## 🚀 Funkcje

| Moduł | Opis |
|---|---|
| 📊 Analiza | Widmo, waterfall, IQ konstelacja, SNR history, AutoTune |
| ⚔️ Ofensywa | Jammer selektywny, spoofer, TPMS, GSM, Drone Attack |
| 🛡 Defensywa | Whitelist/Blacklist, FHSS Hop Detector, GeoFence, anomalie 24h |
| 🔬 Dekoder | ADS-B, sensor ISM, Custom Protocol Builder, rolling code |
| 🧠 SIGINT | Signal timeline, heatmapa 24h, eksport KML, triangulacja |
| 📡 Protokoły | 28 pasm, 16 protokołów, historia skanów |
| 🔍 Sweep | 0–6 GHz sweep, Min/Max/Current hold, tabela wyników |
| 🔊 Audio | AM/FM/USB/LSB demod, RDS decoder, recorder |
| 🎯 Misja | Mission Planner, Target DB, OPSEC Checklist |
| ☯ Sztuka Wojny | 13 rozdziałów Sun Tzu, Scenario Simulator, OPSEC Score |

---

## 🖥️ Instalacja (Windows)

### Wymagania
- Python 3.10+
- HackRF One lub Two (tryb DEMO bez urządzenia)

### Instalacja
```bash
# Sklonuj repozytorium
git clone https://github.com/Jezior91/rf-imperium.git
cd rf-imperium

# Zainstaluj zależności
install.bat

# Uruchom
launch.bat
```

### Zależności Python
```bash
pip install PyQt6 numpy scipy matplotlib pyaudio hackrf
```

---

## 🌐 Demo przeglądarkowe

Otwórz `demo.html` w przeglądarce — działa bez HackRF, pełna symulacja.

---

## ⚠️ Disclaimer

Tylko do celów edukacyjnych i testów własnej infrastruktury. Nadawanie sygnałów RF bez licencji jest niezgodne z prawem.

---

## 📜 Licencja

MIT License — użyj swobodnie, zachowaj attribution.
