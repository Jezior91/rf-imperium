@echo off
title RF Imperium v5.0 MAX
cd /d "%~dp0"
echo ============================================
echo  RF Imperium v5.0 MAX — HackRF Panel
echo  Zakres: 1 Hz - 6 GHz
echo ============================================
echo.
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Aplikacja zakonczyla sie z bledem %errorlevel%
    echo Uruchom launch_debug.bat aby zobaczyc szczegoly
    pause
)
