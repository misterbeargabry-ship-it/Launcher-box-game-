"""
Download in background con scrittura atomica e verifica SHA-256 esplicita.
Scaricare soltanto file da fonti affidabili e autorizzate.
"""
import hashlib
import os
import re
import time
from urllib.parse import urlparse, unquote

import requests
from PySide6.QtCore import QThread, Signal
from database import get_connection, now_iso


class DownloadWorker(QThread):
    progress_changed = Signal(int, int)
    status_changed = Signal(int, str)
    finished_ok = Signal(int, str, str)
    finished_error = Signal(int, str)

    def __init__(self, download_id, url, dest_path, expected_sha256=None, parent=None):
        super().__init__(parent)
        self.download_id = download_id
        self.url = url
        self.dest_path = dest_path
        self.expected_sha256 = (expected_sha256 or "").strip().lower() or None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        part_path = self.dest_path + ".part"
        try:
            self.status_changed.emit(self.download_id, "Connessione in corso...")
            with requests.get(self.url, stream=True, timeout=(15, 60),
                              headers={"User-Agent": "GAMEBOX-PC/2.0"}) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0) or 0)
                os.makedirs(os.path.dirname(os.path.abspath(self.dest_path)), exist_ok=True)
                digest = hashlib.sha256()
                downloaded = 0
                last_emit = 0.0
                self.status_changed.emit(self.download_id, "Download in corso...")
                with open(part_path, "wb") as stream:
                    for chunk in response.iter_content(chunk_size=262144):
                        if self._cancelled:
                            raise InterruptedError("Download annullato dall'utente.")
                        if not chunk:
                            continue
                        stream.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if total > 0 and now - last_emit >= 0.1:
                            self.progress_changed.emit(self.download_id,
                                min(99, int(downloaded * 100 / total)))
                            last_emit = now
                    stream.flush()
                    os.fsync(stream.fileno())
                if total and downloaded != total:
                    raise IOError(f"Download incompleto: ricevuti {downloaded} byte su {total}.")

            sha256_hex = digest.hexdigest()
            if self.expected_sha256 and sha256_hex.lower() != self.expected_sha256:
                raise ValueError("Verifica SHA-256 FALLITA: il file non corrisponde all'hash atteso. File non pubblicato.")
            os.replace(part_path, self.dest_path)
            self.progress_changed.emit(self.download_id, 100)
            self.status_changed.emit(self.download_id, "Completato e verificato" if self.expected_sha256 else "Completato (hash non fornito)")
            self.finished_ok.emit(self.download_id, self.dest_path, sha256_hex)
        except InterruptedError as e:
            self._cleanup(part_path)
            self.status_changed.emit(self.download_id, "Annullato")
            self.finished_error.emit(self.download_id, str(e))
        except (requests.exceptions.RequestException, OSError, ValueError) as e:
            self._cleanup(part_path)
            self.finished_error.emit(self.download_id, str(e))
        except Exception as e:
            self._cleanup(part_path)
            self.finished_error.emit(self.download_id, f"Errore imprevisto: {e}")

    def _cleanup(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


class DownloadManager:
    def __init__(self, settings):
        self.settings = settings
        self._workers = {}

    def add_download_record(self, name, url, expected_sha256=None):
        url = (url or "").strip()
        if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
            raise ValueError("Inserisci un URL HTTP o HTTPS valido.")
        expected = (expected_sha256 or "").strip().lower() or None
        if expected and not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("L'hash SHA-256 deve contenere esattamente 64 caratteri esadecimali.")
        downloads_dir = os.path.abspath(os.path.expanduser(self.settings.get("downloads_path")))
        os.makedirs(downloads_dir, exist_ok=True)
        raw_name = os.path.basename(unquote(urlparse(url).path))
        filename = re.sub(r"[^A-Za-z0-9._ -]", "_", raw_name).strip(" .")
        if not filename:
            filename = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "download")) + ".bin"
        stem, ext = os.path.splitext(filename)
        dest_path = os.path.join(downloads_dir, filename)
        counter = 1
        while os.path.exists(dest_path) or os.path.exists(dest_path + ".part"):
            dest_path = os.path.join(downloads_dir, f"{stem}_{counter}{ext}")
            counter += 1
        conn = get_connection()
        cur = conn.execute("""INSERT INTO downloads
            (name, url, dest_path, expected_sha256, status, progress, date_added)
            VALUES (?, ?, ?, ?, 'In attesa', 0, ?)""",
            ((name or "").strip() or filename, url, dest_path, expected, now_iso()))
        conn.commit()
        download_id = cur.lastrowid
        conn.close()
        return download_id

    def list_downloads(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM downloads ORDER BY date_added DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def remove_download(self, download_id, delete_file=False):
        if download_id in self._workers:
            raise ValueError("Annulla e attendi la fine del download prima di rimuoverlo.")
        conn = get_connection()
        row = conn.execute("SELECT dest_path FROM downloads WHERE id = ?", (download_id,)).fetchone()
        conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
        conn.commit()
        conn.close()
        if delete_file and row and row["dest_path"]:
            for path in (row["dest_path"], row["dest_path"] + ".part"):
                try:
                    if os.path.isfile(path): os.remove(path)
                except OSError:
                    pass

    def start_download(self, download_id):
        if download_id in self._workers:
            raise ValueError("Questo download e' gia' in esecuzione.")
        conn = get_connection()
        row = conn.execute("SELECT * FROM downloads WHERE id = ?", (download_id,)).fetchone()
        conn.close()
        if not row:
            raise ValueError("Download non trovato nel database.")
        if row["status"] == "In corso":
            raise ValueError("Download gia' in corso.")
        worker = DownloadWorker(download_id, row["url"], row["dest_path"], row["expected_sha256"])
        worker.progress_changed.connect(self._on_progress)
        worker.status_changed.connect(self._on_status)
        worker.finished_ok.connect(self._on_finished_ok)
        worker.finished_error.connect(self._on_finished_error)
        worker.finished.connect(lambda did=download_id: self._workers.pop(did, None))
        self._workers[download_id] = worker
        self._set_status(download_id, "In corso", 0)
        worker.start()
        return worker

    def cancel_download(self, download_id):
        worker = self._workers.get(download_id)
        if worker:
            worker.cancel()

    def _on_progress(self, download_id, percent):
        conn = get_connection()
        conn.execute("UPDATE downloads SET progress = ? WHERE id = ?", (percent, download_id))
        conn.commit(); conn.close()

    def _on_status(self, download_id, status):
        self._set_status(download_id, status)

    def _on_finished_ok(self, download_id, dest_path, sha256_hex):
        conn = get_connection()
        row = conn.execute("SELECT expected_sha256 FROM downloads WHERE id = ?", (download_id,)).fetchone()
        expected = (row["expected_sha256"] or "").strip().lower() if row else ""
        verified = int(bool(expected) and expected == sha256_hex.lower())
        status = "Completato e verificato" if verified else "Completato (non verificato)"
        conn.execute("""UPDATE downloads SET status=?, progress=100, actual_sha256=?, verified=? WHERE id=?""",
                     (status, sha256_hex, verified, download_id))
        conn.commit(); conn.close()

    def _on_finished_error(self, download_id, message):
        self._set_status(download_id, "Annullato" if "annullato" in message.lower() else f"Errore: {message}")

    def _set_status(self, download_id, status, progress=None):
        conn = get_connection()
        if progress is None:
            conn.execute("UPDATE downloads SET status=? WHERE id=?", (status, download_id))
        else:
            conn.execute("UPDATE downloads SET status=?, progress=? WHERE id=?", (status, progress, download_id))
        conn.commit(); conn.close()

    def verify_file_sha256(self, file_path, expected_sha256):
        if not os.path.isfile(file_path) or not re.fullmatch(r"[0-9a-fA-F]{64}", (expected_sha256 or "").strip()):
            return False
        digest = hashlib.sha256()
        with open(file_path, "rb") as stream:
            for chunk in iter(lambda: stream.read(262144), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected_sha256.strip().lower()
