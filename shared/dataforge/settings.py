from __future__ import annotations

import os
from pathlib import Path


def _resolve_root() -> Path:
    env_root = os.getenv("DATAFORGE_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


ROOT_DIR = _resolve_root()
INSTANCE_DIR = Path(
    os.getenv("DATAFORGE_INSTANCE_DIR", ROOT_DIR / "services" / "web" / "instance")
)
PROJECTS_DIR = Path(
    os.getenv("DATAFORGE_PROJECTS_DIR", INSTANCE_DIR / "projects")
)
