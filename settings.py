"""
Impostazioni persistenti di GAMEBOX PC.
"""
import json
import os
from app_paths import writable_data_dir, app_storage_dir

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = writable_data_dir()
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "resolution": "1600x900", "theme": "Scuro Blu/Viola", "language": "Italiano",
    "library_path": os.path.join(BASE_DIR, "Games"),
    "apk_path": os.path.join(BASE_DIR, "APK"),
    "downloads_path": os.path.join(BASE_DIR, "Downloads"),
    "adb_path": "adb", "aapt_path": "aapt", "emulator_path": "",
    "controller_enabled": True,
    "shortcuts_path": os.path.join(BASE_DIR, "Games", "Collegamenti"),
}


class Settings:
    def __init__(self, path=None):
        self.path = path or SETTINGS_PATH
        self._data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    self._data.update(saved)
            except (json.JSONDecodeError, OSError, TypeError):
                # Conserva il file danneggiato per consentire un recupero manuale.
                backup = self.path + ".corrotto"
                try:
                    if not os.path.exists(backup):
                        os.replace(self.path, backup)
                except OSError:
                    pass
                self.save()
        else:
            self.save()
        for key in ("library_path", "apk_path", "downloads_path", "shortcuts_path"):
            value = self._data.get(key)
            if value:
                try:
                    os.makedirs(os.path.expanduser(value), exist_ok=True)
                except OSError:
                    pass

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, self.path)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def set_many(self, mapping):
        self._data.update(mapping)

    def all(self):
        return dict(self._data)

    def resolution_tuple(self):
        try:
            w, h = self.get("resolution", "1600x900").lower().split("x")
            w, h = int(w), int(h)
            if 800 <= w <= 7680 and 600 <= h <= 4320:
                return w, h
        except (ValueError, AttributeError, TypeError):
            pass
        return 1600, 900
