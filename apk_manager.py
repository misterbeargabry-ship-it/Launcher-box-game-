"""
apk_manager.py
---------------
Gestisce i file APK Android tramite ADB (Android Debug Bridge), collegandosi
a un emulatore Android gia' installato (es. BlueStacks, NoxPlayer, Memu,
Android Studio Emulator) o a un dispositivo fisico con debug USB attivo.

IMPORTANTE: GAMEBOX PC NON esegue APK nativamente su Windows. Windows non e'
in grado di eseguire pacchetti Android senza un motore di compatibilita'
(un emulatore). Questo modulo richiede quindi ADB funzionante e un
emulatore/dispositivo Android collegato e visibile con `adb devices`.
"""

import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional

from database import get_connection, now_iso


class ApkManagerError(Exception):
    """Errore applicativo sollevato dall'ApkManager (mostrato all'utente)."""
    pass


class ApkManager:
    def __init__(self, settings):
        self.settings = settings

    # ------------------------------------------------------------------ #
    # ADB di base
    # ------------------------------------------------------------------ #
    @property
    def adb_path(self) -> str:
        return self.settings.get("adb_path", "adb")

    def _run_adb(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        cmd = [self.adb_path] + args
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            raise ApkManagerError(
                "ADB non trovato. Installa Android Platform Tools e imposta il "
                "percorso corretto nelle Impostazioni (Configurazione emulatore Android)."
            )
        except subprocess.TimeoutExpired:
            raise ApkManagerError("Comando ADB scaduto (timeout). Controlla la connessione.")

    def check_adb_available(self) -> bool:
        try:
            result = self._run_adb(["version"], timeout=10)
            return result.returncode == 0
        except ApkManagerError:
            return False

    def list_devices(self) -> List[str]:
        """Restituisce l'elenco dei device/emulatori Android visibili ad ADB."""
        result = self._run_adb(["devices"])
        if result.returncode != 0:
            raise ApkManagerError(f"Errore ADB: {result.stderr.strip()}")
        devices = []
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if line and "\t" in line:
                serial, state = line.split("\t")
                if state == "device":
                    devices.append(serial)
        return devices

    def has_connected_device(self) -> bool:
        try:
            return len(self.list_devices()) > 0
        except ApkManagerError:
            return False

    # ------------------------------------------------------------------ #
    # Import e gestione APK
    # ------------------------------------------------------------------ #
    def import_apk(self, source_path: str) -> str:
        """
        Copia un file APK selezionato dall'utente nella cartella APK/ della
        libreria, cosi' da conservarlo in modo permanente e indipendente
        dalla posizione originale del file.
        """
        if not source_path or not os.path.isfile(source_path):
            raise ApkManagerError(f"File APK non trovato: {source_path}")
        if not source_path.lower().endswith(".apk"):
            raise ApkManagerError("Il file selezionato non e' un pacchetto .apk valido.")

        apk_dir = self.settings.get("apk_path")
        os.makedirs(apk_dir, exist_ok=True)
        dest = os.path.join(apk_dir, os.path.basename(source_path))
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1
        shutil.copy2(source_path, dest)
        return dest

    def guess_package_name(self, apk_path: str) -> Optional[str]:
        """
        Tenta di ricavare il nome del pacchetto Android (es. com.azienda.gioco)
        usando 'aapt dump badging', se lo strumento aapt e' disponibile nel
        sistema (incluso negli Android SDK Build-Tools). Se aapt non e'
        disponibile, restituisce None: l'utente potra' inserirlo manualmente
        nell'interfaccia.
        """
        aapt_path = self.settings.get("aapt_path", "aapt")
        try:
            result = subprocess.run(
                [aapt_path, "dump", "badging", apk_path],
                capture_output=True, text=True, timeout=20,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        match = re.search(r"package: name='([^']+)'", result.stdout)
        return match.group(1) if match else None

    def install_apk(self, apk_path: str) -> None:
        """Installa un APK sull'emulatore/dispositivo collegato tramite ADB."""
        if not os.path.isfile(apk_path):
            raise ApkManagerError(f"File APK non trovato: {apk_path}")
        if not self.has_connected_device():
            raise ApkManagerError(
                "Nessun emulatore o dispositivo Android collegato. Avvia il tuo "
                "emulatore (es. BlueStacks/NoxPlayer) e verifica che sia "
                "visibile con ADB, oppure collega un dispositivo con debug USB attivo."
            )
        result = self._run_adb(["install", "-r", apk_path], timeout=120)
        if result.returncode != 0 or "Success" not in result.stdout:
            raise ApkManagerError(
                f"Installazione fallita: {result.stdout.strip()} {result.stderr.strip()}"
            )

    def uninstall_package(self, package_name: str) -> None:
        if not package_name:
            raise ApkManagerError("Nome pacchetto mancante.")
        result = self._run_adb(["uninstall", package_name], timeout=60)
        if result.returncode != 0 or "Success" not in result.stdout:
            raise ApkManagerError(f"Disinstallazione fallita: {result.stdout.strip()}")

    def list_installed_packages(self) -> List[str]:
        """Elenca i pacchetti Android di terze parti installati sull'emulatore."""
        result = self._run_adb(["shell", "pm", "list", "packages", "-3"])
        if result.returncode != 0:
            raise ApkManagerError(f"Errore ADB: {result.stderr.strip()}")
        packages = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.replace("package:", "").strip())
        return packages

    def launch_package(self, package_name: str) -> None:
        """
        Avvia un'app Android installata tramite il suo package name,
        usando 'monkey' per lanciare l'activity principale (metodo standard
        e affidabile via ADB, non richiede conoscere il nome dell'activity).
        """
        if not package_name:
            raise ApkManagerError(
                "Nome pacchetto non impostato per questo APK. Modificalo e "
                "inserisci il package name (es. com.azienda.gioco)."
            )
        if not self.has_connected_device():
            raise ApkManagerError("Nessun emulatore/dispositivo Android collegato.")
        result = self._run_adb([
            "shell", "monkey", "-p", package_name,
            "-c", "android.intent.category.LAUNCHER", "1",
        ], timeout=30)
        if result.returncode != 0:
            raise ApkManagerError(f"Impossibile avviare l'app: {result.stderr.strip()}")
