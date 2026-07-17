"""Pluggable message-history storage for flask-chat-events.

A :class:`MessageStore` decouples *where* chat history lives from the event
machinery. Bind one to :class:`~flask_chat_events.chat.ChatEvents` and messages
are persisted automatically as they are emitted, and served back on demand via
``chat.history(room)``.

The bundled :class:`InMemoryMessageStore` is process-local and per-room capped —
perfect for a single-process app or tests. Implement the :class:`MessageStore`
interface to back history with Redis, a database, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from threading import RLock
from typing import Any, Deque, Dict, List, Optional

Message = Dict[str, Any]

__all__ = ["MessageStore", "InMemoryMessageStore"]


class MessageStore(ABC):
    """Interface for chat message history backends."""

    @abstractmethod
    def add(self, room: str, message: Message) -> None:
        """Persist ``message`` (a payload dict) for ``room``."""

    @abstractmethod
    def history(self, room: str, limit: Optional[int] = None) -> List[Message]:
        """Return stored messages for ``room``, oldest first.

        When ``limit`` is given, only the most recent ``limit`` messages are
        returned.
        """

    @abstractmethod
    def get(self, room: str, message_id: str) -> Optional[Message]:
        """Return the stored message with ``message_id`` or ``None``."""

    @abstractmethod
    def edit(self, room: str, message_id: str, text: str, *, edited_at: str) -> Optional[Message]:
        """Update the ``text`` of a stored message and return it (or ``None``)."""

    @abstractmethod
    def delete(self, room: str, message_id: str) -> bool:
        """Remove a stored message. Return ``True`` if one was removed."""

    @abstractmethod
    def clear(self, room: Optional[str] = None) -> None:
        """Drop history for ``room``, or all rooms when ``room`` is ``None``."""


class InMemoryMessageStore(MessageStore):
    """Thread-safe, process-local store keeping the last N messages per room.

    ``max_per_room`` bounds memory: once a room holds that many messages the
    oldest are dropped automatically.
    """

    def __init__(self, max_per_room: int = 200) -> None:
        if max_per_room <= 0:
            raise ValueError("max_per_room must be a positive integer.")
        self._max = max_per_room
        self._rooms: Dict[str, Deque[Message]] = defaultdict(self._new_deque)
        self._lock = RLock()

    def _new_deque(self) -> Deque[Message]:
        return deque(maxlen=self._max)

    def add(self, room: str, message: Message) -> None:
        with self._lock:
            self._rooms[room].append(dict(message))

    def history(self, room: str, limit: Optional[int] = None) -> List[Message]:
        with self._lock:
            messages = list(self._rooms.get(room, ()))
        if limit is not None and limit >= 0:
            messages = messages[-limit:]
        return messages

    def get(self, room: str, message_id: str) -> Optional[Message]:
        with self._lock:
            for message in self._rooms.get(room, ()):
                if message.get("id") == message_id:
                    return dict(message)
        return None

    def edit(self, room: str, message_id: str, text: str, *, edited_at: str) -> Optional[Message]:
        with self._lock:
            for message in self._rooms.get(room, ()):
                if message.get("id") == message_id:
                    message["text"] = text
                    message["edited_at"] = edited_at
                    return dict(message)
        return None

    def delete(self, room: str, message_id: str) -> bool:
        with self._lock:
            bucket = self._rooms.get(room)
            if not bucket:
                return False
            kept = [m for m in bucket if m.get("id") != message_id]
            if len(kept) == len(bucket):
                return False
            bucket.clear()
            bucket.extend(kept)
            return True

    def clear(self, room: Optional[str] = None) -> None:
        with self._lock:
            if room is None:
                self._rooms.clear()
            else:
                self._rooms.pop(room, None)
