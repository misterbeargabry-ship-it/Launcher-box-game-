"""
Database SQLite di GAMEBOX PC. Il file resta nella cartella data scrivibile
accanto all'eseguibile, anche quando il programma e' creato con PyInstaller.
"""
import os
import sqlite3
from datetime import datetime
from app_paths import writable_data_dir

DATA_DIR = writable_data_dir()
DB_PATH = os.path.join(DATA_DIR, "gamebox.db")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_connection(db_path=None):
    ensure_data_dir()
    conn = sqlite3.connect(db_path or DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('exe', 'apk')), path TEXT NOT NULL,
        cover_path TEXT, category TEXT DEFAULT 'Generale', installed INTEGER DEFAULT 1,
        package_name TEXT, play_count INTEGER DEFAULT 0, last_played TEXT,
        date_added TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, url TEXT NOT NULL,
        dest_path TEXT, expected_sha256 TEXT, actual_sha256 TEXT,
        status TEXT DEFAULT 'In attesa', progress INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0, date_added TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS settings_kv (
        key TEXT PRIMARY KEY, value TEXT)""")
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    init_db()
    print(f"Database inizializzato correttamente in: {DB_PATH}")
