"""
dataforge/api/websocket/manager.py
────────────────────────────────────
WebSocket connection manager with multi-tab support.

Architecture:
    User (user_id)
    └── Tab 1 (WebSocket connection)
    └── Tab 2 (WebSocket connection)
    └── Tab N (WebSocket connection)

Supported operations:
    broadcast_to_user(user_id, event, data) → sends to all tabs of a user
    broadcast_all(event, data)              → sends to all connected users
    broadcast_workspace(upload_id, event, data) → sends to users watching an upload
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket

from dataforge.api.utils.json import safe_dumps

log = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with per-user, per-tab granularity.

    Thread-safety: All methods are async-safe (run within the same event loop).
    """

    def __init__(self):
        # {user_id: set[WebSocket]}
        self._user_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # {upload_id: set[int]} — which users are watching which uploads
        self._upload_watchers: Dict[int, Set[int]] = defaultdict(set)
        # Global lock to protect the sets during connect/disconnect
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, user_id: int, upload_id: Optional[int] = None):
        """Accept a new WebSocket connection for user_id."""
        await websocket.accept()
        async with self._lock:
            self._user_connections[user_id].add(websocket)
            if upload_id is not None:
                self._upload_watchers[upload_id].add(user_id)
        log.info("WS connect: user_id=%s tabs=%d", user_id, len(self._user_connections[user_id]))

    async def disconnect(self, websocket: WebSocket, user_id: int, upload_id: Optional[int] = None):
        """Remove a WebSocket connection."""
        async with self._lock:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
                # Remove user from all upload watcher sets
                for watchers in self._upload_watchers.values():
                    watchers.discard(user_id)
            if upload_id is not None and upload_id in self._upload_watchers:
                # Only remove if no more tabs from this user are watching
                if user_id not in self._user_connections:
                    self._upload_watchers[upload_id].discard(user_id)
        log.debug("WS disconnect: user_id=%s", user_id)

    # ── Send helpers ──────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: int, event: str, data: dict):
        """Push an event to all browser tabs of a specific user."""
        payload = safe_dumps({"event": event, "data": data})
        dead: list[WebSocket] = []

        connections = set(self._user_connections.get(user_id, set()))
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Clean up dead connections without holding the lock during sends
        if dead:
            async with self._lock:
                for ws in dead:
                    self._user_connections[user_id].discard(ws)

    async def broadcast_to_workspace(self, upload_id: int, event: str, data: dict):
        """Push an event to all users currently watching an upload (workspace)."""
        watchers = set(self._upload_watchers.get(upload_id, set()))
        for user_id in watchers:
            await self.send_to_user(user_id, event, data)

    async def broadcast_all(self, event: str, data: dict):
        """Push an event to every connected user (admin/system events)."""
        all_users = list(self._user_connections.keys())
        for user_id in all_users:
            await self.send_to_user(user_id, event, data)

    # ── Introspection ─────────────────────────────────────────────────────────

    def connected_user_ids(self) -> list[int]:
        return list(self._user_connections.keys())

    def tab_count(self, user_id: int) -> int:
        return len(self._user_connections.get(user_id, set()))

    def total_connections(self) -> int:
        return sum(len(v) for v in self._user_connections.values())


# ── Module-level singleton (created in app lifespan) ─────────────────────────
ws_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> ConnectionManager:
    global ws_manager
    if ws_manager is None:
        ws_manager = ConnectionManager()
    return ws_manager
