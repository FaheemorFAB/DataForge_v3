"""
shared/dataforge/supabase_storage.py
════════════════════════════
Supabase Storage integration for DataForge.

Handles CSV datasets and pickle objects (cleaned DataFrames, trained models,
EDA HTML etc.) with a graceful local-disk fallback so the app keeps working
even when SUPABASE_URL / SUPABASE_KEY are not yet configured.

Setup
─────
1. pip install supabase
2. Add to .env:
       SUPABASE_URL=https://<project>.supabase.co
       SUPABASE_SERVICE_KEY=<service_role_key>   ← use service role, NOT anon
       SUPABASE_BUCKET=dataforge-datasets        ← create this bucket first
3. In Supabase dashboard → Storage → New bucket → name: dataforge-datasets
   Set to private (not public) so signed URLs are required.

Storage layout
──────────────
  dataforge-datasets/
    users/{user_id}/uploads/{upload_id}/
      raw.csv          ← original upload
      clean.csv        ← cleaned DataFrame
      clean.pkl        ← cleaned DataFrame pickle
      model.pkl        ← trained AutoML model
      eda.html         ← EDA HTML report

Usage
─────
    from dataforge.supabase_storage import SupabaseStorage, STORAGE_OK

    store = SupabaseStorage()

    # Upload
    path = store.upload_dataframe(user_id=1, upload_id=42, df=df, key="raw")

    # Download
    df = store.download_dataframe(path)

    # Pickle
    path = store.upload_pickle(user_id=1, upload_id=42, key="model", obj=model)
    model = store.download_pickle(path)
"""

import io
import logging
import os
import pickle
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv

from .settings import ROOT_DIR, PROJECTS_DIR

load_dotenv(override=True, dotenv_path=ROOT_DIR / ".env")
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Prefer the service-role key (bypasses Row Level Security)
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY", "")
)
BUCKET_NAME  = os.getenv("SUPABASE_BUCKET", "dataforge-datasets")

# Public flag so app.py can show a warning when storage isn't configured
STORAGE_OK = bool(SUPABASE_URL and SUPABASE_KEY)

# Local fallback directory (used when Supabase is unavailable)
_LOCAL_FALLBACK_DIR = PROJECTS_DIR


class SupabaseStorage:
    """
    Thin wrapper around the Supabase Storage Python SDK.

    Every public method falls back to local disk if Supabase is not
    configured, so the app degrades gracefully during development.
    """

    def __init__(self):
        self._client = None

    # ── Internal client ───────────────────────────────────────────────────────

    def _get_client(self):
        if self._client:
            return self._client
        if not STORAGE_OK:
            raise RuntimeError(
                "Supabase not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
            )
        try:
            from supabase import create_client
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
            return self._client
        except ImportError:
            raise RuntimeError(
                "supabase not installed. Run: pip install supabase"
            )

    # ── Low-level byte operations ─────────────────────────────────────────────

    def upload_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to Supabase Storage. Returns the storage path."""
        client = self._get_client()
        try:
            bucket = client.storage.from_(BUCKET_NAME)
            # upsert=True overwrites existing files at the same path
            bucket.upload(
                path,
                data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            log.info("SupabaseStorage: uploaded %d bytes → %s", len(data), path)
            return path
        except Exception as exc:
            log.error("SupabaseStorage.upload_bytes failed (%s): %s", path, exc)
            raise

    def download_bytes(self, path: str) -> bytes:
        """Download raw bytes from Supabase Storage."""
        client = self._get_client()
        try:
            data = client.storage.from_(BUCKET_NAME).download(path)
            log.info("SupabaseStorage: downloaded %d bytes ← %s", len(data), path)
            return data
        except Exception as exc:
            log.error("SupabaseStorage.download_bytes failed (%s): %s", path, exc)
            raise

    def delete_path(self, path: str) -> bool:
        """Delete a single file from Supabase Storage."""
        try:
            client = self._get_client()
            client.storage.from_(BUCKET_NAME).remove([path])
            return True
        except Exception as exc:
            log.warning("SupabaseStorage.delete_path failed (%s): %s", path, exc)
            return False

    def delete_upload(self, user_id: int, upload_id: int) -> bool:
        """Delete ALL files for an upload (called on dataset deletion)."""
        try:
            prefix = f"users/{user_id}/uploads/{upload_id}/"
            client = self._get_client()
            files  = client.storage.from_(BUCKET_NAME).list(prefix)
            if files:
                paths = [f"{prefix}{f['name']}" for f in files]
                client.storage.from_(BUCKET_NAME).remove(paths)
                log.info(
                    "SupabaseStorage: deleted %d files for upload %s",
                    len(paths), upload_id,
                )
            return True
        except Exception as exc:
            log.warning("SupabaseStorage.delete_upload failed: %s", exc)
            return False

    # ── DataFrame helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _df_path(user_id: int, upload_id: int, key: str) -> str:
        return f"users/{user_id}/uploads/{upload_id}/{key}.csv"

    def upload_dataframe(
        self,
        user_id:   int,
        upload_id: int,
        df:        pd.DataFrame,
        key:       str = "raw",
    ) -> str:
        """
        Serialise df as CSV and upload to Supabase Storage.
        Returns the storage path (store this in Upload.storage_path).
        """
        if not STORAGE_OK:
            return self._save_local_df(user_id, upload_id, df, key)

        path      = self._df_path(user_id, upload_id, key)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return self.upload_bytes(path, csv_bytes, "text/csv")

    def download_dataframe(self, storage_path: str) -> Optional[pd.DataFrame]:
        """
        Download a CSV from Supabase Storage and return as DataFrame.
        Returns None on failure rather than raising, so callers can fall back.
        """
        if not STORAGE_OK:
            return self._load_local_df(storage_path)
        try:
            data = self.download_bytes(storage_path)
            return pd.read_csv(io.BytesIO(data))
        except Exception as exc:
            log.warning("SupabaseStorage.download_dataframe failed: %s", exc)
            return None

    # ── Pickle helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _pkl_path(user_id: int, upload_id: int, key: str) -> str:
        return f"users/{user_id}/uploads/{upload_id}/{key}.pkl"

    def upload_pickle(
        self,
        user_id:   int,
        upload_id: int,
        key:       str,
        obj:       Any,
    ) -> str:
        """
        Pickle `obj` and upload to Supabase Storage.
        Returns the storage path.
        """
        if not STORAGE_OK:
            return self._save_local_pkl(user_id, upload_id, key, obj)

        path      = self._pkl_path(user_id, upload_id, key)
        pkl_bytes = pickle.dumps(obj)
        return self.upload_bytes(path, pkl_bytes, "application/octet-stream")

    def download_pickle(self, storage_path: str) -> Any:
        """
        Download a pickle from Supabase Storage and deserialise it.
        Returns None on failure rather than raising.
        """
        if not STORAGE_OK:
            return self._load_local_pkl(storage_path)
        try:
            data = self.download_bytes(storage_path)
            return pickle.loads(data)
        except Exception as exc:
            log.warning("SupabaseStorage.download_pickle failed: %s", exc)
            return None

    # ── HTML helpers (for EDA / reports) ─────────────────────────────────────

    def upload_html(
        self,
        user_id:   int,
        upload_id: int,
        key:       str,
        html:      str,
    ) -> str:
        """Upload an HTML string to Supabase Storage. Returns storage path."""
        if not STORAGE_OK:
            return self._save_local_bytes(
                user_id, upload_id, key + ".html", html.encode("utf-8")
            )
        path = f"users/{user_id}/uploads/{upload_id}/{key}.html"
        return self.upload_bytes(path, html.encode("utf-8"), "text/html")

    def download_html(self, storage_path: str) -> Optional[str]:
        """Download an HTML file from Supabase Storage. Returns None on failure."""
        if not STORAGE_OK:
            return self._load_local_str(storage_path)
        try:
            data = self.download_bytes(storage_path)
            return data.decode("utf-8")
        except Exception as exc:
            log.warning("SupabaseStorage.download_html failed: %s", exc)
            return None

    # ── Signed URL ────────────────────────────────────────────────────────────

    def signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Return a short-lived signed URL for a private Supabase Storage file.
        Useful for serving reports or model downloads directly from the CDN.
        Returns None if Supabase is not configured.
        """
        if not STORAGE_OK:
            return None
        try:
            client = self._get_client()
            resp   = client.storage.from_(BUCKET_NAME).create_signed_url(
                storage_path, expires_in
            )
            return resp.get("signedURL") or resp.get("signedUrl")
        except Exception as exc:
            log.warning("SupabaseStorage.signed_url failed: %s", exc)
            return None

    # ── Local fallback helpers ────────────────────────────────────────────────

    def _local_dir(self, user_id: int, upload_id: int) -> Path:
        d = _LOCAL_FALLBACK_DIR / str(upload_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_local_df(
        self, user_id: int, upload_id: int, df: pd.DataFrame, key: str
    ) -> str:
        p = self._local_dir(user_id, upload_id) / f"{key}.csv"
        df.to_csv(p, index=False)
        log.debug("SupabaseStorage[local]: saved df → %s", p)
        return str(p)

    def _load_local_df(self, path: str) -> Optional[pd.DataFrame]:
        p = Path(path)
        if not p.exists():
            return None
        try:
            return pd.read_csv(p)
        except Exception:
            return None

    def _save_local_pkl(
        self, user_id: int, upload_id: int, key: str, obj: Any
    ) -> str:
        p = self._local_dir(user_id, upload_id) / f"{key}.pkl"
        with open(p, "wb") as f:
            pickle.dump(obj, f)
        log.debug("SupabaseStorage[local]: saved pickle → %s", p)
        return str(p)

    def _load_local_pkl(self, path: str) -> Any:
        p = Path(path)
        if not p.exists():
            return None
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def _save_local_bytes(
        self, user_id: int, upload_id: int, filename: str, data: bytes
    ) -> str:
        p = self._local_dir(user_id, upload_id) / filename
        p.write_bytes(data)
        return str(p)

    def _load_local_str(self, path: str) -> Optional[str]:
        p = Path(path)
        if not p.exists():
            return None
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None


# ── Module-level singleton ────────────────────────────────────────────────────
_store: Optional[SupabaseStorage] = None


def get_store() -> SupabaseStorage:
    """Return the module-level SupabaseStorage singleton."""
    global _store
    if _store is None:
        _store = SupabaseStorage()
    return _store
