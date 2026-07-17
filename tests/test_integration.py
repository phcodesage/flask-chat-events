"""End-to-end tests that drive the example chat app through *real* Flask-SocketIO.

Unlike test_chat.py (which mocks emit), these use Flask-SocketIO's own test
client, so events actually travel through the server, rooms and the wire
protocol. This is the proof that the extension works in a live application.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Make examples/ importable without installing it as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from chat_app import create_app  # noqa: E402

ROOM = "general"


def _events_by_name(received: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index a test client's received events by event name -> payload."""
    return {item["name"]: item["args"][0] for item in received}


@pytest.fixture
def server():
    """A fresh app + SocketIO server for each test."""
    app, socketio, chat = create_app()
    return app, socketio, chat


def _join(client, user_id: str) -> None:
    client.emit("join", {"room": ROOM, "user_id": user_id})
    client.get_received()  # drain the presence event from joining


def test_message_broadcasts_to_everyone_in_room(server) -> None:
    app, socketio, _ = server
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    _join(alice, "alice")
    _join(bob, "bob")

    alice.emit("send_message", {"room": ROOM, "user_id": "alice", "text": "hi bob"})

    for who in (alice, bob):
        events = _events_by_name(who.get_received())
        assert "chat:message" in events
        payload = events["chat:message"]
        assert payload["room"] == ROOM
        assert payload["user_id"] == "alice"
        assert payload["text"] == "hi bob"
        assert payload["id"]
        assert payload["created_at"]


def test_typing_indicator_reaches_other_client(server) -> None:
    app, socketio, _ = server
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    _join(alice, "alice")
    _join(bob, "bob")

    alice.emit("typing", {"room": ROOM, "user_id": "alice"})
    bob_events = _events_by_name(bob.get_received())
    assert bob_events["chat:typing:start"] == {"room": ROOM, "user_id": "alice"}

    alice.emit("stop_typing", {"room": ROOM, "user_id": "alice"})
    bob_events = _events_by_name(bob.get_received())
    assert bob_events["chat:typing:stop"] == {"room": ROOM, "user_id": "alice"}


def test_read_receipt_flow(server) -> None:
    app, socketio, _ = server
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    _join(alice, "alice")
    _join(bob, "bob")

    alice.emit("send_message", {"room": ROOM, "user_id": "alice", "text": "seen?"})
    msg = _events_by_name(bob.get_received())["chat:message"]

    bob.emit("mark_read", {"room": ROOM, "message_id": msg["id"], "user_id": "bob"})
    read = _events_by_name(alice.get_received())["chat:read"]
    assert read == {"room": ROOM, "message_id": msg["id"], "user_id": "bob"}


def test_presence_on_join(server) -> None:
    app, socketio, _ = server
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    _join(alice, "alice")

    # Bob joins; alice (already in the room) should see bob's presence.
    bob.emit("join", {"room": ROOM, "user_id": "bob"})
    alice_events = _events_by_name(alice.get_received())
    assert alice_events["presence:update"] == {"user_id": "bob", "status": "online"}


def test_room_isolation(server) -> None:
    """A message in one room must not leak to a client in a different room."""
    app, socketio, _ = server
    alice = socketio.test_client(app)
    carol = socketio.test_client(app)
    _join(alice, "alice")  # room "general"
    carol.emit("join", {"room": "other-room", "user_id": "carol"})
    carol.get_received()

    alice.emit("send_message", {"room": ROOM, "user_id": "alice", "text": "private"})

    carol_events = _events_by_name(carol.get_received())
    assert "chat:message" not in carol_events
