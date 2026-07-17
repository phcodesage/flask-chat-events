"""Standardized event names and constants for flask-chat-events."""

from __future__ import annotations

from typing import Final, FrozenSet

# Socket.IO event names. These are the canonical names emitted by ChatEvents.
EVENT_MESSAGE: Final[str] = "chat:message"
EVENT_EDIT: Final[str] = "chat:edit"
EVENT_DELETE: Final[str] = "chat:delete"
EVENT_TYPING_START: Final[str] = "chat:typing:start"
EVENT_TYPING_STOP: Final[str] = "chat:typing:stop"
EVENT_READ: Final[str] = "chat:read"
EVENT_PRESENCE: Final[str] = "presence:update"
EVENT_USER_LIST: Final[str] = "presence:list"
EVENT_HISTORY: Final[str] = "chat:history"

# Presence statuses that a user is allowed to broadcast.
STATUS_ONLINE: Final[str] = "online"
STATUS_OFFLINE: Final[str] = "offline"
STATUS_AWAY: Final[str] = "away"

VALID_STATUSES: Final[FrozenSet[str]] = frozenset(
    {STATUS_ONLINE, STATUS_OFFLINE, STATUS_AWAY}
)

# Default *inbound* (client -> server) event names that ``register_handlers``
# listens on. Override any of these via :class:`InboundEvents` when a client
# uses different names.
INBOUND_JOIN: Final[str] = "join"
INBOUND_LEAVE: Final[str] = "leave"
INBOUND_SEND_MESSAGE: Final[str] = "send_message"
INBOUND_EDIT_MESSAGE: Final[str] = "edit_message"
INBOUND_DELETE_MESSAGE: Final[str] = "delete_message"
INBOUND_TYPING: Final[str] = "typing"
INBOUND_MARK_READ: Final[str] = "mark_read"
