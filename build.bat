@echo off
setlocal
cd /d "%~dp0"
title GAMEBOX PC - Build v2.0

echo.
echo ==========================================
echo       GAMEBOX PC v2.0 - BUILD WINDOWS
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERRORE] Python 3.10+ non trovato. Installalo da python.org.
  pause
  exit /b 1
)

if not exist venv\Scripts\python.exe python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo [BUILD] Creazione GAMEBOX.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name GAMEBOX ^
  --icon "assets\icons\gamebox.ico" ^
  --add-data "assets;assets" ^
  --hidden-import PySide6.QtSvg ^
  main.py
if errorlevel 1 goto error

if not exist "dist\Games" mkdir "dist\Games"
if not exist "dist\APK" mkdir "dist\APK"
if not exist "dist\Downloads" mkdir "dist\Downloads"
if not exist "dist\data" mkdir "dist\data"

echo.
echo BUILD COMPLETATA.
echo Avvia dist\GAMEBOX.exe. I dati verranno salvati nelle cartelle
echo data, Games, APK e Downloads accanto all'eseguibile.
echo.
pause
exit /b 0

:error
echo.
echo [ERRORE] Build non riuscita. Controlla il messaggio precedente.
pause
exit /b 1
