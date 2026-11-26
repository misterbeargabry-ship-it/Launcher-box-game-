#!/usr/bin/env python3
"""
main.py
--------
Punto di ingresso di GAMEBOX PC. Inizializza il database, le impostazioni
e avvia l'interfaccia grafica PySide6.

Avvio:
    python main.py
oppure tramite il file Avvia_GAMEBOX.bat su Windows.
"""

import sys
import os

# Assicura che la cartella del progetto sia nel path, cosi' gli import
# relativi (ui.*, game_manager, ecc.) funzionano anche eseguendo da
# un eseguibile generato con PyInstaller.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from database import init_db
from settings import Settings
from game_manager import GameManager
from apk_manager import ApkManager
from download_manager import DownloadManager
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen
from ui.styles import DARK_PURPLE_BLUE_THEME
from app_paths import resource_path


def main():
    # Inizializza il database SQLite (crea le tabelle se mancanti)
    try:
        init_db()
    except Exception as e:
        print(f"Errore critico durante l'inizializzazione del database: {e}")
        sys.exit(1)

    settings = Settings()

    app = QApplication(sys.argv)
    app.setApplicationName("GAMEBOX PC")
    app.setStyleSheet(DARK_PURPLE_BLUE_THEME)

    icon_path = resource_path("assets", "icons", "gamebox.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    game_manager = GameManager(settings)
    apk_manager = ApkManager(settings)
    download_manager = DownloadManager(settings)

    window = MainWindow(settings, game_manager, apk_manager, download_manager)

    # Schermata di avvio animata: la finestra principale viene creata
    # subito (cosi' e' gia' pronta) ma mostrata solo a boot concluso.
    splash = SplashScreen()

    def show_main_window():
        splash.close()
        window.show()

    splash.finished.connect(show_main_window)
    splash.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
