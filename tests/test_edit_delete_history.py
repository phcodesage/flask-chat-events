"""Unit tests for edit/delete events, store integration, and history helpers."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from flask_chat_events import (
    ChatEvents,
    EVENT_DELETE,
    EVENT_EDIT,
    EVENT_HISTORY,
    EVENT_USER_LIST,
    EmptyMessageError,
    InMemoryMessageStore,
    MissingMessageIdError,
    NotInitializedError,
    PresenceRegistry,
)

ISO_8601 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@pytest.fixture
def socketio() -> MagicMock:
    return MagicMock()


# --------------------------------------------------------------------------- #
# edit() / delete()                                                           #
# --------------------------------------------------------------------------- #
def test_edit_event_and_payload(socketio: MagicMock) -> None:
    chat = ChatEvents(socketio)
    payload = chat.edit(room="general", message_id=7, user_id="u", text="fixed")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_EDIT
    assert data == payload
    assert data["id"] == "7"
    assert data["room"] == "general"
    assert data["user_id"] == "u"
    assert data["text"] == "fixed"
    assert ISO_8601.match(data["edited_at"])
    assert socketio.emit.call_args.kwargs["room"] == "general"


def test_edit_empty_text_rejected(socketio: MagicMock) -> None:
    with pytest.raises(EmptyMessageError):
        ChatEvents(socketio).edit(room="g", message_id="1", user_id="u", text="  ")


def test_edit_missing_message_id(socketio: MagicMock) -> None:
    with pytest.raises(MissingMessageIdError):
        ChatEvents(socketio).edit(room="g", message_id="", user_id="u", text="t")


def test_delete_event_and_payload(socketio: MagicMock) -> None:
    chat = ChatEvents(socketio)
    payload = chat.delete(room="general", message_id="7", user_id="u")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_DELETE
    assert data == payload == {"id": "7", "room": "general", "user_id": "u"}
    assert socketio.emit.call_args.kwargs["room"] == "general"


def test_delete_missing_message_id(socketio: MagicMock) -> None:
    with pytest.raises(MissingMessageIdError):
        ChatEvents(socketio).delete(room="g", message_id=None, user_id="u")


# --------------------------------------------------------------------------- #
# store integration                                                           #
# --------------------------------------------------------------------------- #
def test_message_auto_persists_to_store(socketio: MagicMock) -> None:
    store = InMemoryMessageStore()
    chat = ChatEvents(socketio, store=store)
    chat.message(room="general", user_id="u", text="hi")
    history = chat.history("general")
    assert len(history) == 1
    assert history[0]["text"] == "hi"


def test_edit_updates_stored_message(socketio: MagicMock) -> None:
    store = InMemoryMessageStore()
    chat = ChatEvents(socketio, store=store)
    msg = chat.message(room="general", user_id="u", text="old")
    chat.edit(room="general", message_id=msg["id"], user_id="u", text="new")
    assert chat.history("general")[0]["text"] == "new"
    assert "edited_at" in chat.history("general")[0]


def test_delete_removes_stored_message(socketio: MagicMock) -> None:
    store = InMemoryMessageStore()
    chat = ChatEvents(socketio, store=store)
    msg = chat.message(room="general", user_id="u", text="bye")
    chat.delete(room="general", message_id=msg["id"], user_id="u")
    assert chat.history("general") == []


def test_history_without_store_raises(socketio: MagicMock) -> None:
    with pytest.raises(NotInitializedError):
        ChatEvents(socketio).history("general")


def test_message_decorator_applied_before_emit_and_store(socketio: MagicMock) -> None:
    store = InMemoryMessageStore()
    chat = ChatEvents(
        socketio,
        store=store,
        message_decorator=lambda p: {**p, "avatar_color": "#abc"},
    )
    payload = chat.message(room="general", user_id="u", text="hi")
    assert payload["avatar_color"] == "#abc"
    _event, emitted = socketio.emit.call_args.args
    assert emitted["avatar_color"] == "#abc"
    assert chat.history("general")[0]["avatar_color"] == "#abc"


def test_send_history_emits_history_event(socketio: MagicMock) -> None:
    store = InMemoryMessageStore()
    chat = ChatEvents(socketio, store=store)
    chat.message(room="general", user_id="u", text="one")
    socketio.reset_mock()
    data = chat.send_history("general")
    event, emitted = socketio.emit.call_args.args
    assert event == EVENT_HISTORY
    assert emitted["room"] == "general"
    assert [m["text"] for m in emitted["messages"]] == ["one"]
    assert data == emitted


# --------------------------------------------------------------------------- #
# broadcast_user_list                                                         #
# --------------------------------------------------------------------------- #
def test_broadcast_user_list_all(socketio: MagicMock) -> None:
    reg = PresenceRegistry()
    reg.connect("s1", "alice", avatar_color="#111")
    chat = ChatEvents(socketio, registry=reg)
    data = chat.broadcast_user_list()
    event, emitted = socketio.emit.call_args.args
    assert event == EVENT_USER_LIST
    assert emitted["room"] is None
    assert emitted["users"] == [{"user_id": "alice", "avatar_color": "#111"}]
    # No room/to kwarg -> Flask-SocketIO broadcasts to everyone.
    assert "room" not in socketio.emit.call_args.kwargs
    assert "to" not in socketio.emit.call_args.kwargs
    assert data == emitted


def test_broadcast_user_list_room(socketio: MagicMock) -> None:
    reg = PresenceRegistry()
    reg.connect("s1", "alice")
    reg.join("s1", "general")
    chat = ChatEvents(socketio, registry=reg)
    chat.broadcast_user_list(room="general")
    _event, emitted = socketio.emit.call_args.args
    assert emitted["room"] == "general"
    assert socketio.emit.call_args.kwargs["room"] == "general"


def test_broadcast_user_list_without_registry_raises(socketio: MagicMock) -> None:
    with pytest.raises(NotInitializedError):
        ChatEvents(socketio).broadcast_user_list()
