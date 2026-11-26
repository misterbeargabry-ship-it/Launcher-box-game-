@echo off
REM ============================================================
REM  Avvia_GAMEBOX.bat - Avvia GAMEBOX PC direttamente da sorgente
REM  (senza bisogno di generare l'eseguibile con PyInstaller)
REM ============================================================

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERRORE] Python non trovato nel PATH. Installa Python 3.10+ da python.org
    pause
    exit /b 1
)

if not exist venv (
    echo Primo avvio rilevato: creazione ambiente virtuale e installazione dipendenze...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Avvio di GAMEBOX PC...
python main.py

if errorlevel 1 (
    echo.
    echo [ERRORE] GAMEBOX PC si e' chiuso con un errore. Controlla il messaggio sopra.
    pause
)
