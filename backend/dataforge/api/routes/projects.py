"""
dataforge/api/routes/projects.py
──────────────────────────────────
Projects routes: list, restore from Supabase, delete.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser
from dataforge.api.repositories.upload import upload_repo
from dataforge.api.storage.manager import clear_store, exists, load, save
from dataforge.api.utils.helpers import time_ago
from dataforge.api.utils.json import safe_jsonable
from dataforge.db import db_get

log = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])


@router.get("/projects", summary="List all projects for current user")
async def api_projects(current_user: CurrentUser):
    uploads = upload_repo.list_for_user(current_user.id, limit=100)
    out = []
    for u in uploads:
        uid = u.get("id")
        has_clean   = exists(uid, "df_clean")
        has_eda     = exists(uid, "eda_html")
        has_automl  = exists(uid, "automl_meta")
        profile     = load(uid, "profile") or {}
        out.append({
            "id": uid,
            "filename": u.get("filename", ""),
            "rows": u.get("rows", 0),
            "cols": u.get("cols", 0),
            "missing_pct": u.get("missing_pct", 0),
            "source_type": u.get("source_type", "csv"),
            "uploaded_at": u.get("uploaded_at"),
            "time_ago": time_ago(u.get("uploaded_at")),
            "has_clean": has_clean,
            "has_eda": has_eda,
            "has_automl": has_automl,
            "numeric": profile.get("numeric", 0),
        })
    return JSONResponse(content=safe_jsonable(out))


@router.post("/restore/{upload_id}", summary="Restore a project dataset from Supabase Storage")
async def api_restore(
    current_user: CurrentUser,
    upload_id: int = Path(...),
):
    up = db_get("uploads", upload_id)
    if not up or up.get("user_id") != current_user.id:
        raise HTTPException(404, "Upload not found")

    restored = False
    for key in ("df_clean", "df_raw"):
        df = load(upload_id, key)
        if df is not None:
            save(upload_id, key, df)
            restored = True
            break

    if not restored:
        try:
            from dataforge.supabase_storage import get_store, STORAGE_OK
            if STORAGE_OK:
                store = get_store()
                user_id = up.get("user_id")
                for remote_key, local_key in [("clean", "df_clean"), ("raw", "df_raw")]:
                    path = f"users/{user_id}/uploads/{upload_id}/{remote_key}.parquet"
                    obj = store.download_dataframe(path)
                    if obj is not None:
                        save(upload_id, local_key, obj)
                        restored = True
                        break
        except Exception as exc:
            log.warning("Supabase restore failed for upload %d: %s", upload_id, exc)

    return {"ok": True, "restored": restored}


@router.delete("/delete/{upload_id}", summary="Delete a project and all its data")
async def api_delete(
    current_user: CurrentUser,
    upload_id: int = Path(...),
):
    up = db_get("uploads", upload_id)
    if not up or up.get("user_id") != current_user.id:
        raise HTTPException(404, "Upload not found")

    # Clear disk storage
    clear_store(upload_id)

    # Delete from Supabase
    upload_repo.delete(upload_id)

    # Best-effort Supabase Storage cleanup
    try:
        from dataforge.supabase_storage import get_store, STORAGE_OK
        if STORAGE_OK:
            user_id = up.get("user_id")
            store = get_store()
            for rkey in ("raw", "clean", "profile", "model_pkl", "eda_html"):
                for ext in (".parquet", ".json", ".joblib", ".html"):
                    try:
                        store.delete(f"users/{user_id}/uploads/{upload_id}/{rkey}{ext}")
                    except Exception:
                        pass
    except Exception:
        pass

    return {"ok": True}
