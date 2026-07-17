"""Unit tests for the ChatEvents public API.

SocketIO.emit is mocked so the tests assert on event name, payload and room
without needing a running server.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from flask_chat_events import (
    ChatEvents,
    EmptyMessageError,
    EVENT_MESSAGE,
    EVENT_PRESENCE,
    EVENT_READ,
    EVENT_TYPING_START,
    EVENT_TYPING_STOP,
    InvalidStatusError,
    MissingRoomError,
    MissingUserIdError,
    NotInitializedError,
)

ISO_8601 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@pytest.fixture
def socketio() -> MagicMock:
    """A mock SocketIO instance exposing ``emit``."""
    return MagicMock()


@pytest.fixture
def chat(socketio: MagicMock) -> ChatEvents:
    """A ChatEvents bound to the mock SocketIO."""
    return ChatEvents(socketio)


# --------------------------------------------------------------------------- #
# Initialization                                                              #
# --------------------------------------------------------------------------- #
def test_direct_initialization(socketio: MagicMock) -> None:
    chat = ChatEvents(socketio)
    assert chat.socketio is socketio


def test_factory_initialization(socketio: MagicMock) -> None:
    chat = ChatEvents()
    chat.init_app(socketio)
    assert chat.socketio is socketio


def test_unbound_raises() -> None:
    chat = ChatEvents()
    with pytest.raises(NotInitializedError):
        chat.message(room="general", user_id="1", text="hi")


# --------------------------------------------------------------------------- #
# message()                                                                   #
# --------------------------------------------------------------------------- #
def test_message_event_and_payload(chat: ChatEvents, socketio: MagicMock) -> None:
    payload = chat.message(room="general", user_id=15, text="Hello")

    socketio.emit.assert_called_once()
    event, data = socketio.emit.call_args.args
    assert event == EVENT_MESSAGE
    assert data == payload
    assert socketio.emit.call_args.kwargs["room"] == "general"

    assert data["room"] == "general"
    assert data["user_id"] == "15"
    assert data["text"] == "Hello"
    assert data["id"]
    assert ISO_8601.match(data["created_at"])


def test_message_generates_created_at_and_id(chat: ChatEvents) -> None:
    payload = chat.message(room="r", user_id="u", text="t")
    assert payload["id"]
    assert ISO_8601.match(payload["created_at"])


def test_message_respects_explicit_id_and_created_at(chat: ChatEvents) -> None:
    payload = chat.message(
        room="r",
        user_id="u",
        text="t",
        id="abc",
        created_at="2020-01-01T00:00:00+00:00",
    )
    assert payload["id"] == "abc"
    assert payload["created_at"] == "2020-01-01T00:00:00+00:00"


def test_message_missing_room(chat: ChatEvents) -> None:
    with pytest.raises(MissingRoomError):
        chat.message(room="", user_id="u", text="t")


def test_message_missing_user_id(chat: ChatEvents) -> None:
    with pytest.raises(MissingUserIdError):
        chat.message(room="r", user_id=None, text="t")


def test_message_empty_text(chat: ChatEvents) -> None:
    with pytest.raises(EmptyMessageError):
        chat.message(room="r", user_id="u", text="   ")


# --------------------------------------------------------------------------- #
# typing_start() / typing_stop()                                              #
# --------------------------------------------------------------------------- #
def test_typing_start(chat: ChatEvents, socketio: MagicMock) -> None:
    payload = chat.typing_start(room="general", user_id="7")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_TYPING_START
    assert data == {"room": "general", "user_id": "7"}
    assert socketio.emit.call_args.kwargs["room"] == "general"
    assert payload == data


def test_typing_stop(chat: ChatEvents, socketio: MagicMock) -> None:
    payload = chat.typing_stop(room="general", user_id="7")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_TYPING_STOP
    assert data == {"room": "general", "user_id": "7"}
    assert socketio.emit.call_args.kwargs["room"] == "general"
    assert payload == data


def test_typing_missing_room(chat: ChatEvents) -> None:
    with pytest.raises(MissingRoomError):
        chat.typing_start(room=None, user_id="7")


def test_typing_missing_user_id(chat: ChatEvents) -> None:
    with pytest.raises(MissingUserIdError):
        chat.typing_stop(room="general", user_id="")


# --------------------------------------------------------------------------- #
# read()                                                                      #
# --------------------------------------------------------------------------- #
def test_read(chat: ChatEvents, socketio: MagicMock) -> None:
    payload = chat.read(room="general", message_id=42, user_id="7")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_READ
    assert data == {"room": "general", "message_id": "42", "user_id": "7"}
    assert socketio.emit.call_args.kwargs["room"] == "general"
    assert payload == data


def test_read_missing_room(chat: ChatEvents) -> None:
    with pytest.raises(MissingRoomError):
        chat.read(room="", message_id="1", user_id="7")


def test_read_missing_user_id(chat: ChatEvents) -> None:
    with pytest.raises(MissingUserIdError):
        chat.read(room="general", message_id="1", user_id=None)


# --------------------------------------------------------------------------- #
# presence()                                                                  #
# --------------------------------------------------------------------------- #
def test_presence_default_status(chat: ChatEvents, socketio: MagicMock) -> None:
    payload = chat.presence(user_id="7")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_PRESENCE
    assert data == {"user_id": "7", "status": "online"}
    assert payload == data
    # No room -> broadcast, so no room kwarg was set.
    assert "room" not in socketio.emit.call_args.kwargs


def test_presence_explicit_status_and_room(
    chat: ChatEvents, socketio: MagicMock
) -> None:
    payload = chat.presence(user_id="7", status="away", room="general")
    event, data = socketio.emit.call_args.args
    assert event == EVENT_PRESENCE
    assert data == {"user_id": "7", "status": "away"}
    assert socketio.emit.call_args.kwargs["room"] == "general"
    assert payload == data


def test_presence_invalid_status(chat: ChatEvents) -> None:
    with pytest.raises(InvalidStatusError):
        chat.presence(user_id="7", status="banana")


def test_presence_missing_user_id(chat: ChatEvents) -> None:
    with pytest.raises(MissingUserIdError):
        chat.presence(user_id="", status="online")
