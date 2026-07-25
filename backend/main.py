"""DataForge FastAPI — entry point.

IMPORTANT: load_dotenv MUST happen before any dataforge imports
so that db.py (which reads env vars at module level) gets the values.
"""
from pathlib import Path

# ── Load .env before any dataforge imports ────────────────────────────────────
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent          # backend/
_ROOT = _HERE.parent                             # DataForge_v3-main/

# Try project root first (.env sits next to frontend/ and backend/)
_loaded = load_dotenv(_ROOT / ".env", override=True)
if not _loaded:
    # Fallback: .env inside backend/
    load_dotenv(_HERE / ".env", override=True)

# ── Now safe to import the app ────────────────────────────────────────────────
import uvicorn
from dataforge.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
