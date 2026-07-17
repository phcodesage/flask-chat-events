"""Presence and room-membership tracking for flask-chat-events.

A :class:`PresenceRegistry` remembers which connection (Socket.IO ``sid``)
belongs to which user, what rooms it has joined, and any per-connection metadata
(display name, avatar color, …). This is the state every chat app otherwise
re-implements by hand as ad-hoc ``ONLINE_USERS`` dicts.

The registry is deliberately transport-agnostic: it stores facts, it does not
emit events. :func:`~flask_chat_events.handlers.register_handlers` wires it to
Socket.IO connect/disconnect/join/leave.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional, Set

__all__ = ["PresenceRegistry"]


@dataclass
class _Connection:
    user_id: str
    meta: Dict[str, Any] = field(default_factory=dict)
    rooms: Set[str] = field(default_factory=set)


class PresenceRegistry:
    """Track connections, their users, rooms, and metadata.

    Users may hold several simultaneous connections (multiple tabs/devices);
    lookups such as :meth:`online_users` and :meth:`users_in` de-duplicate by
    ``user_id`` so each user appears once.
    """

    def __init__(self) -> None:
        self._by_sid: Dict[str, _Connection] = {}
        self._lock = RLock()

    # -- lifecycle --------------------------------------------------------- #
    def connect(self, sid: str, user_id: str, **meta: Any) -> None:
        """Register a new connection for ``user_id`` with optional metadata."""
        with self._lock:
            self._by_sid[sid] = _Connection(user_id=str(user_id), meta=dict(meta))

    def disconnect(self, sid: str) -> Optional[Dict[str, Any]]:
        """Remove a connection.

        Returns a summary ``{"user_id", "meta", "rooms", "was_last"}`` for the
        removed connection, or ``None`` if ``sid`` was unknown. ``was_last`` is
        ``True`` when the user has no remaining connections afterwards.
        """
        with self._lock:
            conn = self._by_sid.pop(sid, None)
            if conn is None:
                return None
            was_last = not self._any_sid_for(conn.user_id)
            return {
                "user_id": conn.user_id,
                "meta": dict(conn.meta),
                "rooms": set(conn.rooms),
                "was_last": was_last,
            }

    # -- rooms ------------------------------------------------------------- #
    def join(self, sid: str, room: str) -> None:
        """Record that ``sid`` joined ``room``."""
        with self._lock:
            conn = self._by_sid.get(sid)
            if conn is not None:
                conn.rooms.add(str(room))

    def leave(self, sid: str, room: str) -> None:
        """Record that ``sid`` left ``room``."""
        with self._lock:
            conn = self._by_sid.get(sid)
            if conn is not None:
                conn.rooms.discard(str(room))

    def rooms_for(self, sid: str) -> Set[str]:
        """Return the set of rooms a connection is in."""
        with self._lock:
            conn = self._by_sid.get(sid)
            return set(conn.rooms) if conn else set()

    # -- lookups ----------------------------------------------------------- #
    def user_for(self, sid: str) -> Optional[str]:
        """Return the ``user_id`` bound to ``sid`` (or ``None``)."""
        with self._lock:
            conn = self._by_sid.get(sid)
            return conn.user_id if conn else None

    def is_online(self, user_id: str) -> bool:
        """Return whether ``user_id`` has at least one live connection."""
        with self._lock:
            return self._any_sid_for(str(user_id))

    def online_users(self) -> List[Dict[str, Any]]:
        """Return one entry per online user: ``{"user_id", **meta}``."""
        with self._lock:
            return self._dedup(self._by_sid.values())

    def users_in(self, room: str) -> List[Dict[str, Any]]:
        """Return one entry per user currently in ``room``."""
        room = str(room)
        with self._lock:
            conns = [c for c in self._by_sid.values() if room in c.rooms]
            return self._dedup(conns)

    # -- internals --------------------------------------------------------- #
    def _any_sid_for(self, user_id: str) -> bool:
        return any(c.user_id == user_id for c in self._by_sid.values())

    @staticmethod
    def _dedup(conns: Any) -> List[Dict[str, Any]]:
        seen: Set[str] = set()
        users: List[Dict[str, Any]] = []
        for conn in conns:
            if conn.user_id in seen:
                continue
            seen.add(conn.user_id)
            users.append({"user_id": conn.user_id, **conn.meta})
        return users
