@echo off
title RF Imperium v5.0 MAX DEBUG
echo === RF Imperium v5.0 MAX DEBUG MODE ===
echo.
echo Python version:
python --version
echo.
echo Checking packages:
python -c "import PyQt6; print('PyQt6 OK')" 2>&1
python -c "import pyqtgraph; print('pyqtgraph OK')" 2>&1
python -c "import numpy; print('numpy OK')" 2>&1
python -c "import scipy; print('scipy OK')" 2>&1
python -c "import SoapySDR; print('SoapySDR OK')" 2>&1
python -c "import pyvisa; print('pyvisa OK')" 2>&1
python -c "import openai; print('openai OK')" 2>&1
echo.
echo Starting application...
python main.py
echo.
echo Exit code: %errorlevel%
pause
