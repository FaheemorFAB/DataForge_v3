"""
dataforge/api/storage/snapshots.py
───────────────────────────────────
P1-2 & P1-3: Optimistic Concurrency & Content-Addressed Snapshot Manager.
Guarantees:
1. Optimistic Concurrency Control (OCC): Compare-and-swap on version_id; returns 409 on conflict.
2. Immutable Content-Addressed Parquet Snapshots: Every transformation writes a SHA-256 snapshot.
3. Linear Head-Pointer Tracking: df_raw is never mutated; df_clean advances along the snapshot chain.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from filelock import FileLock

from dataforge.api.storage.manager import STORE_DIR, load, save, upath

log = logging.getLogger(__name__)
_OCC_LOCK = threading.RLock()


class ConcurrencyConflictError(Exception):
    """Raised when expected version_id does not match current version_id."""
    def __init__(self, current_version: str, expected_version: Optional[str]):
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__(
            f"Conflict: Dataset version mismatch. Current version: {current_version!r}, "
            f"expected: {expected_version!r}."
        )


class StorageBackend:
    """Abstract interface for dataset and snapshot object storage (P2-2)."""
    def write_bytes(self, key: str, data: bytes) -> None:
        raise NotImplementedError

    def read_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""
    def write_bytes(self, key: str, data: bytes) -> None:
        p = Path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def read_bytes(self, key: str) -> bytes:
        return Path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return Path(key).exists()


class S3StorageBackend(StorageBackend):
    """S3/MinIO compatible object storage backend."""
    def __init__(self, bucket: str, endpoint_url: Optional[str] = None):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self._s3 = None

    def _get_client(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client("s3", endpoint_url=self.endpoint_url)
        return self._s3

    def write_bytes(self, key: str, data: bytes) -> None:
        client = self._get_client()
        client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def read_bytes(self, key: str) -> bytes:
        client = self._get_client()
        resp = client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_active_storage_backend() -> StorageBackend:
    import os
    bucket = os.environ.get("STORAGE_S3_BUCKET") or os.environ.get("S3_BUCKET")
    if bucket:
        endpoint = os.environ.get("STORAGE_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
        return S3StorageBackend(bucket=bucket, endpoint_url=endpoint)
    return LocalStorageBackend()


class SnapshotManager:
    """Manages immutable parquet snapshots and dataset versioning."""

    @classmethod
    def _snapshots_dir(cls, upload_id: str) -> Path:
        p = STORE_DIR / str(upload_id) / "snapshots"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def _manifest_path(cls, upload_id: str) -> Path:
        return cls._snapshots_dir(upload_id) / "manifest.json"

    @classmethod
    def get_version(cls, upload_id: str) -> str:
        """Returns the current version_id for an upload, or 'v0' if unversioned."""
        v = load(upload_id, "version_id")
        if isinstance(v, str) and v.strip():
            return v
        meta = load(upload_id, "meta") or {}
        return meta.get("version_id", "v0")

    @classmethod
    def get_manifest(cls, upload_id: str) -> List[Dict[str, Any]]:
        p = cls._manifest_path(upload_id)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning("Could not read snapshot manifest for %s: %s", upload_id, e)
        return []

    @classmethod
    def commit_snapshot(
        cls,
        upload_id: str,
        df: pd.DataFrame,
        expected_version: Optional[str] = None,
        action: str = "mutation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Executes an atomic compare-and-swap commit:
        1. Verifies expected_version matches current version (raises ConcurrencyConflictError on mismatch).
        2. Content-addresses DataFrame via SHA-256 of snappy parquet bytes.
        3. Writes immutable snapshot parquet.
        4. Updates head pointer (df_clean, version_id, active_snapshot_id).
        Returns: (new_version_id, snapshot_id)
        """
        lock_file = STORE_DIR / str(upload_id) / ".commit.lock"
        with FileLock(str(lock_file)), _OCC_LOCK:
            current_v = cls.get_version(upload_id)

            # Optimistic concurrency check
            if expected_version is not None:
                # Normalize If-Match quotes: e.g. '"v1"' -> 'v1'
                norm_expected = expected_version.strip('"').strip()
                norm_current = current_v.strip('"').strip()
                if norm_expected != "*" and norm_expected != norm_current:
                    raise ConcurrencyConflictError(
                        current_version=norm_current,
                        expected_version=norm_expected,
                    )

            # Compute content-addressed hash
            buf = io.BytesIO()
            try:
                df.to_parquet(buf, index=False, compression="snappy")
            except Exception:
                from dataforge.web.storage import _safe_df_for_parquet
                safe_df = _safe_df_for_parquet(df)
                buf = io.BytesIO()
                safe_df.to_parquet(buf, index=False, compression="snappy")
            parquet_bytes = buf.getvalue()
            sha256 = hashlib.sha256(parquet_bytes).hexdigest()
            snapshot_id = sha256[:16]

            # Save immutable snapshot via active storage backend
            snap_file = cls._snapshots_dir(upload_id) / f"{snapshot_id}.parquet"
            backend = get_active_storage_backend()
            if not backend.exists(str(snap_file)):
                backend.write_bytes(str(snap_file), parquet_bytes)

            # Generate strictly unique, monotonic version_id
            import secrets
            timestamp_ms = int(time.time() * 1000)
            nonce = secrets.token_hex(4)
            new_version_id = f"v_{timestamp_ms}_{nonce}"

            # Update head pointers
            save(upload_id, "df_clean", df)
            save(upload_id, "version_id", new_version_id)
            save(upload_id, "active_snapshot_id", snapshot_id)

            # Update meta if present
            meta = load(upload_id, "meta")
            if isinstance(meta, dict):
                meta["version_id"] = new_version_id
                meta["active_snapshot_id"] = snapshot_id
                save(upload_id, "meta", meta)

            # Append to manifest
            manifest = cls.get_manifest(upload_id)
            entry = {
                "version_id": new_version_id,
                "snapshot_id": snapshot_id,
                "parent_version": current_v,
                "action": action,
                "rows": len(df),
                "cols": df.shape[1],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }
            manifest.append(entry)
            cls._manifest_path(upload_id).write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            return new_version_id, snapshot_id
