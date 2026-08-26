@echo off
echo ============================================
echo  RF Imperium v4.0 — Windows Installer
echo ============================================
echo.

:: Check Python
python --version 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python nie znaleziony!
    echo Pobierz: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Aktualizacja pip...
python -m pip install --upgrade pip --quiet

echo [2/5] Instalacja pakietow podstawowych...
python -m pip install PyQt6 pyqtgraph numpy scipy --quiet

echo [3/5] Instalacja pakietow opcjonalnych...
python -m pip install pyvisa pyvisa-py openai sounddevice soundfile ^
    reportlab scikit-learn joblib websockets --quiet

echo [4/5] Tworzenie katalogu recordings...
if not exist recordings mkdir recordings

echo [5/5] Tworzenie konfiguracji...
if not exist config.json (
    echo {> config.json
    echo   "center_freq": 433920000,>> config.json
    echo   "sample_rate": 2000000,>> config.json
    echo   "lna_gain": 16,>> config.json
    echo   "vga_gain": 20,>> config.json
    echo   "tx_gain": 20,>> config.json
    echo   "tx_enabled": false,>> config.json
    echo   "openai_key": "",>> config.json
    echo   "openai_model": "gpt-4o",>> config.json
    echo   "sa_resource": "",>> config.json
    echo   "sg_resource": "",>> config.json
    echo   "recording_dir": "recordings",>> config.json
    echo   "fft_size": 1024,>> config.json
    echo   "avg_alpha": 0.1>> config.json
    echo }>> config.json
)

echo.
echo ============================================
echo  Instalacja zakonczona!
echo.
echo  UWAGA: Dla HackRF zainstaluj SoapySDR:
echo  https://github.com/pothosware/SoapySDR/wiki
echo  lub: conda install -c conda-forge soapysdr
echo.
echo  Uruchom aplikacje: launch.bat
echo ============================================
pause
