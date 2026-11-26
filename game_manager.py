"""
game_manager.py
----------------
Gestisce la libreria dei giochi: aggiunta, rimozione, ricerca, avvio
dei giochi Windows (.exe) e rilevamento delle applicazioni gia' installate
sul sistema. Tutti i dati sono salvati permanentemente in SQLite tramite
database.py, quindi la libreria sopravvive alla chiusura del programma.
"""

import os
import shutil
import subprocess
import sys
from typing import List, Optional

from database import get_connection, now_iso


class GameManagerError(Exception):
    """Errore applicativo sollevato dal GameManager (mostrato all'utente)."""
    pass


class GameManager:
    def __init__(self, settings):
        self.settings = settings

    # ------------------------------------------------------------------ #
    # Lettura
    # ------------------------------------------------------------------ #
    def list_games(self, category: Optional[str] = None, search: str = "") -> List[dict]:
        conn = get_connection()
        query = "SELECT * FROM games WHERE 1=1"
        params = []
        if category and category != "Tutte":
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND LOWER(name) LIKE ?"
            params.append(f"%{search.lower()}%")
        query += " ORDER BY name COLLATE NOCASE ASC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_game(self, game_id: int) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_categories(self) -> List[str]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT DISTINCT category FROM games ORDER BY category COLLATE NOCASE"
        ).fetchall()
        conn.close()
        return [r["category"] for r in rows]

    def stats(self) -> dict:
        conn = get_connection()
        total = conn.execute("SELECT COUNT(*) AS c FROM games").fetchone()["c"]
        exe_count = conn.execute(
            "SELECT COUNT(*) AS c FROM games WHERE type = 'exe'"
        ).fetchone()["c"]
        apk_count = conn.execute(
            "SELECT COUNT(*) AS c FROM games WHERE type = 'apk'"
        ).fetchone()["c"]
        installed = conn.execute(
            "SELECT COUNT(*) AS c FROM games WHERE installed = 1"
        ).fetchone()["c"]
        most_played = conn.execute(
            "SELECT name, play_count FROM games ORDER BY play_count DESC LIMIT 5"
        ).fetchall()
        recent = conn.execute(
            "SELECT name, last_played FROM games WHERE last_played IS NOT NULL "
            "ORDER BY last_played DESC LIMIT 5"
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "exe_count": exe_count,
            "apk_count": apk_count,
            "installed": installed,
            "most_played": [dict(r) for r in most_played],
            "recent": [dict(r) for r in recent],
        }

    # ------------------------------------------------------------------ #
    # Scrittura
    # ------------------------------------------------------------------ #
    def add_exe_game(self, name: str, exe_path: str, cover_path: str = None,
                      category: str = "Generale") -> int:
        if not exe_path or not os.path.isfile(exe_path):
            raise GameManagerError(f"Il file eseguibile non esiste: {exe_path}")
        if not exe_path.lower().endswith(".exe"):
            raise GameManagerError("Il file selezionato non e' un eseguibile (.exe).")

        cover_path = self._copy_cover(cover_path)

        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO games (name, type, path, cover_path, category,
                                   installed, play_count, date_added)
               VALUES (?, 'exe', ?, ?, ?, 1, 0, ?)""",
            (name.strip(), exe_path, cover_path, category.strip() or "Generale", now_iso()),
        )
        conn.commit()
        game_id = cur.lastrowid
        conn.close()
        return game_id

    def add_apk_entry(self, name: str, apk_path: str, package_name: str = None,
                       cover_path: str = None, category: str = "Android") -> int:
        if not apk_path or not os.path.isfile(apk_path):
            raise GameManagerError(f"Il file APK non esiste: {apk_path}")
        if not apk_path.lower().endswith(".apk"):
            raise GameManagerError("Il file selezionato non e' un pacchetto .apk.")

        cover_path = self._copy_cover(cover_path)

        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO games (name, type, path, cover_path, category,
                                   installed, package_name, play_count, date_added)
               VALUES (?, 'apk', ?, ?, ?, 0, ?, 0, ?)""",
            (name.strip(), apk_path, cover_path, category.strip() or "Android",
             package_name, now_iso()),
        )
        conn.commit()
        game_id = cur.lastrowid
        conn.close()
        return game_id

    def set_installed(self, game_id: int, installed: bool, package_name: str = None):
        conn = get_connection()
        if package_name:
            conn.execute(
                "UPDATE games SET installed = ?, package_name = ? WHERE id = ?",
                (1 if installed else 0, package_name, game_id),
            )
        else:
            conn.execute(
                "UPDATE games SET installed = ? WHERE id = ?",
                (1 if installed else 0, game_id),
            )
        conn.commit()
        conn.close()

    def update_category(self, game_id: int, category: str):
        conn = get_connection()
        conn.execute("UPDATE games SET category = ? WHERE id = ?",
                      (category.strip() or "Generale", game_id))
        conn.commit()
        conn.close()

    def remove_game(self, game_id: int):
        conn = get_connection()
        conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
        conn.commit()
        conn.close()

    def register_play(self, game_id: int):
        conn = get_connection()
        conn.execute(
            "UPDATE games SET play_count = play_count + 1, last_played = ? WHERE id = ?",
            (now_iso(), game_id),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------ #
    # Avvio
    # ------------------------------------------------------------------ #
    def launch_exe(self, game_id: int) -> subprocess.Popen:
        """
        Avvia un gioco Windows tramite il suo eseguibile autorizzato.
        Usa subprocess.Popen con il percorso assoluto, eseguendolo nella
        propria cartella di lavoro (necessario per molti giochi che
        cercano file relativi accanto all'exe).
        """
        game = self.get_game(game_id)
        if not game or game["type"] != "exe":
            raise GameManagerError("Gioco non valido o non di tipo EXE.")
        path = game["path"]
        if not os.path.isfile(path):
            raise GameManagerError(f"Eseguibile non trovato: {path}")

        workdir = os.path.dirname(path)
        try:
            if sys.platform == "win32":
                process = subprocess.Popen([path], cwd=workdir, shell=False)
            else:
                # Ambiente non Windows (es. sviluppo/test su Linux/macOS):
                # non possiamo eseguire un .exe nativamente.
                raise GameManagerError(
                    "L'avvio diretto di file .exe e' supportato solo su Windows."
                )
        except OSError as e:
            raise GameManagerError(f"Impossibile avviare il gioco: {e}")

        self.register_play(game_id)
        return process

    # ------------------------------------------------------------------ #
    # Rilevamento app/giochi installati su Windows
    # ------------------------------------------------------------------ #
    def detect_installed_windows_apps(self) -> List[dict]:
        """
        Scansiona il registro di Windows (chiavi Uninstall) per elencare le
        applicazioni installate sul sistema, cosi' l'utente puo' importarle
        rapidamente in libreria. Funziona solo su Windows.
        """
        results = []
        if sys.platform != "win32":
            return results

        import winreg  # disponibile solo su Windows

        uninstall_keys = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hive, subkey in uninstall_keys:
            try:
                key = winreg.OpenKey(hive, subkey)
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub = winreg.OpenKey(key, sub_name)
                    try:
                        display_name = winreg.QueryValueEx(sub, "DisplayName")[0]
                    except OSError:
                        continue
                    try:
                        icon_or_exe = winreg.QueryValueEx(sub, "DisplayIcon")[0]
                    except OSError:
                        icon_or_exe = ""
                    exe_path = icon_or_exe.split(",")[0].strip('"') if icon_or_exe else ""
                    if exe_path and exe_path.lower().endswith(".exe") and os.path.isfile(exe_path):
                        results.append({"name": display_name, "path": exe_path})
                except OSError:
                    continue
            key.Close()

        # Rimuove duplicati mantenendo l'ordine
        seen = set()
        unique_results = []
        for r in results:
            if r["path"] not in seen:
                seen.add(r["path"])
                unique_results.append(r)
        return unique_results

    # ------------------------------------------------------------------ #
    # Collegamenti rapidi
    # ------------------------------------------------------------------ #
    def create_shortcut(self, game_id: int) -> str:
        """
        Crea un collegamento rapido per il gioco. Se pywin32 e' disponibile
        (solo Windows) crea un vero file .lnk; altrimenti crea un file .bat
        funzionante che avvia comunque il gioco con un doppio clic.
        """
        game = self.get_game(game_id)
        if not game:
            raise GameManagerError("Gioco non trovato.")

        shortcuts_dir = self.settings.get("shortcuts_path")
        os.makedirs(shortcuts_dir, exist_ok=True)
        safe_name = "".join(c for c in game["name"] if c.isalnum() or c in " _-").strip() or "gioco"

        if sys.platform == "win32":
            try:
                import win32com.client  # richiede pywin32
                lnk_path = os.path.join(shortcuts_dir, f"{safe_name}.lnk")
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(lnk_path)
                shortcut.Targetpath = game["path"]
                shortcut.WorkingDirectory = os.path.dirname(game["path"])
                shortcut.IconLocation = game["path"]
                shortcut.save()
                return lnk_path
            except ImportError:
                pass  # ricade sul fallback .bat

        bat_path = os.path.join(shortcuts_dir, f"{safe_name}.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write(f'start "" "{game["path"]}"\n')
        return bat_path

    # ------------------------------------------------------------------ #
    # Utility interne
    # ------------------------------------------------------------------ #
    def _copy_cover(self, cover_path: Optional[str]) -> Optional[str]:
        """Copia l'immagine di copertina scelta dall'utente dentro assets/covers."""
        if not cover_path or not os.path.isfile(cover_path):
            return None
        covers_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "assets", "covers")
        os.makedirs(covers_dir, exist_ok=True)
        dest = os.path.join(covers_dir, os.path.basename(cover_path))
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1
        try:
            shutil.copy2(cover_path, dest)
            return dest
        except OSError:
            return None
