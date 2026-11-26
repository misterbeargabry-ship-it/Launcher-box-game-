"""Percorsi distinti per risorse in sola lettura e dati persistenti."""
import os
import sys


def resource_path(*parts):
    """Percorso di una risorsa inclusa nel pacchetto PyInstaller o nel sorgente."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_storage_dir():
    """Cartella utente scrivibile, anche se GAMEBOX e' installato in Program Files."""
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(root, "GAMEBOX_PC")
    os.makedirs(path, exist_ok=True)
    return path


def writable_data_dir():
    path = os.path.join(app_storage_dir(), "data")
    os.makedirs(path, exist_ok=True)
    return path
