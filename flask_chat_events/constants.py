"""Standardized event names and constants for flask-chat-events."""

from __future__ import annotations

from typing import Final, FrozenSet

# Socket.IO event names. These are the canonical names emitted by ChatEvents.
EVENT_MESSAGE: Final[str] = "chat:message"
EVENT_TYPING_START: Final[str] = "chat:typing:start"
EVENT_TYPING_STOP: Final[str] = "chat:typing:stop"
EVENT_READ: Final[str] = "chat:read"
EVENT_PRESENCE: Final[str] = "presence:update"

# Presence statuses that a user is allowed to broadcast.
STATUS_ONLINE: Final[str] = "online"
STATUS_OFFLINE: Final[str] = "offline"
STATUS_AWAY: Final[str] = "away"

VALID_STATUSES: Final[FrozenSet[str]] = frozenset(
    {STATUS_ONLINE, STATUS_OFFLINE, STATUS_AWAY}
)
