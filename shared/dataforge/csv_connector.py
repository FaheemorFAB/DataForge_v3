"""
CSV / File Connector
════════════════════
Handles CSV ingestion from:
  1. Direct file upload (already done in app.py)
  2. Watched folder — a directory that is scanned for new CSV files

Usage::

    from dataforge.data_sources.csv_connector import CSVConnector

    conn = CSVConnector(watch_dir="/data/drop", upload_id=42)
    df   = conn.load_latest()   # returns newest file in dir as DataFrame

File-watcher (optional, requires watchdog):
    conn.start_watcher(callback=my_fn)   # calls my_fn(df) on each new file
    conn.stop_watcher()
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

log = logging.getLogger(__name__)


class CSVConnector:
    """
    Loads a CSV (or the latest CSV in a watched directory) as a pandas DataFrame.
    Optional file-system watcher triggers a callback on each new file.
    """

    def __init__(self, watch_dir: str | Path | None = None, upload_id: int | None = None):
        self.watch_dir  = Path(watch_dir) if watch_dir else None
        self.upload_id  = upload_id
        self._observer  = None

    # ── One-shot load ─────────────────────────────────────────────────────────
    def load_file(self, path: str | Path) -> pd.DataFrame:
        """Load a single CSV file."""
        return pd.read_csv(path)

    def load_latest(self) -> Optional[pd.DataFrame]:
        """Return the most recently modified CSV in watch_dir."""
        if not self.watch_dir or not self.watch_dir.is_dir():
            return None
        csvs = sorted(self.watch_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csvs:
            return None
        log.info("CSVConnector: loading latest file %s", csvs[0])
        return pd.read_csv(csvs[0])

    def list_available(self) -> list[dict]:
        """List all CSV files in watch_dir with metadata."""
        if not self.watch_dir or not self.watch_dir.is_dir():
            return []
        results = []
        for p in sorted(self.watch_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
            st = p.stat()
            results.append({
                "name":     p.name,
                "path":     str(p),
                "size_kb":  round(st.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            })
        return results

    # ── File watcher ──────────────────────────────────────────────────────────
    def start_watcher(self, callback: Callable[[pd.DataFrame, str], None]):
        """
        Watch watch_dir for new CSV files.
        Calls callback(df, filename) when a new .csv is detected.
        Requires: pip install watchdog
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            watch_dir = self.watch_dir

            class _Handler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(".csv"):
                        try:
                            df = pd.read_csv(event.src_path)
                            fname = Path(event.src_path).name
                            log.info("CSVConnector watcher: new file %s", fname)
                            callback(df, fname)
                        except Exception as exc:
                            log.warning("CSVConnector: failed to load %s — %s", event.src_path, exc)

            self._observer = Observer()
            self._observer.schedule(_Handler(), str(watch_dir), recursive=False)
            self._observer.start()
            log.info("CSVConnector: watching %s", watch_dir)

        except ImportError:
            log.warning("watchdog not installed — file watching disabled. pip install watchdog")

    def stop_watcher(self):
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
            log.info("CSVConnector: watcher stopped.")
