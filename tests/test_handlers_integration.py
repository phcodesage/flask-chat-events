"""End-to-end tests for the batteries-included register_handlers() wiring.

Drives examples/registered_app.py through Flask-SocketIO's real test client, so
connect/join/send/edit/delete/typing/read, history replay and presence lists all
travel through an actual server.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from registered_app import create_app  # noqa: E402

ROOM = "general"


def _by_name(received: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    # Last event of each name wins (fine for these single-event assertions).
    return {item["name"]: item["args"][0] for item in received}


def _all(received: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
    return [item["args"][0] for item in received if item["name"] == name]


@pytest.fixture
def server():
    app, socketio, chat = create_app()
    return app, socketio, chat


def _client(app, socketio, user: str):
    return socketio.test_client(app, query_string=f"user={user}")


def test_connect_requires_authentication(server) -> None:
    app, socketio, _ = server
    anon = socketio.test_client(app)  # no ?user=
    assert anon.is_connected() is False


def test_join_replays_history_to_new_client(server) -> None:
    app, socketio, _ = server
    alice = _client(app, socketio, "alice")
    alice.get_received()  # drain connect presence/user-list
    alice.emit("join", {"room": ROOM})
    alice.get_received()

    alice.emit("send_message", {"room": ROOM, "text": "first"})
    alice.get_received()

    bob = _client(app, socketio, "bob")
    bob.get_received()
    bob.emit("join", {"room": ROOM})
    history = _by_name(bob.get_received()).get("chat:history")
    assert history is not None
    assert [m["text"] for m in history["messages"]] == ["first"]


def test_send_message_broadcasts_and_persists(server) -> None:
    app, socketio, chat = server
    alice = _client(app, socketio, "alice")
    bob = _client(app, socketio, "bob")
    for c in (alice, bob):
        c.emit("join", {"room": ROOM})
        c.get_received()

    alice.emit("send_message", {"room": ROOM, "text": "hi bob"})
    msg = _by_name(bob.get_received())["chat:message"]
    assert msg["user_id"] == "alice"
    assert msg["text"] == "hi bob"
    assert chat.history(ROOM)[-1]["text"] == "hi bob"


def test_user_id_is_server_authoritative(server) -> None:
    """A client claiming someone else's user_id is ignored."""
    app, socketio, _ = server
    alice = _client(app, socketio, "alice")
    bob = _client(app, socketio, "bob")
    for c in (alice, bob):
        c.emit("join", {"room": ROOM})
        c.get_received()

    # alice lies, claiming to be "carol"
    alice.emit("send_message", {"room": ROOM, "user_id": "carol", "text": "spoof"})
    msg = _by_name(bob.get_received())["chat:message"]
    assert msg["user_id"] == "alice"  # not "carol"


def test_edit_and_delete_flow(server) -> None:
    app, socketio, chat = server
    alice = _client(app, socketio, "alice")
    bob = _client(app, socketio, "bob")
    for c in (alice, bob):
        c.emit("join", {"room": ROOM})
        c.get_received()

    alice.emit("send_message", {"room": ROOM, "text": "typpo"})
    msg = _by_name(bob.get_received())["chat:message"]
    mid = msg["id"]

    alice.emit("edit_message", {"room": ROOM, "message_id": mid, "text": "typo"})
    edit = _by_name(bob.get_received())["chat:edit"]
    assert edit["id"] == mid and edit["text"] == "typo"
    assert chat.history(ROOM)[-1]["text"] == "typo"

    alice.emit("delete_message", {"room": ROOM, "message_id": mid})
    delete = _by_name(bob.get_received())["chat:delete"]
    assert delete["id"] == mid
    assert chat.history(ROOM) == []


def test_typing_indicator_excludes_self(server) -> None:
    app, socketio, _ = server
    alice = _client(app, socketio, "alice")
    bob = _client(app, socketio, "bob")
    for c in (alice, bob):
        c.emit("join", {"room": ROOM})
        c.get_received()

    alice.emit("typing", {"room": ROOM, "is_typing": True})
    assert _by_name(bob.get_received())["chat:typing:start"]["user_id"] == "alice"
    assert "chat:typing:start" not in _by_name(alice.get_received())

    alice.emit("typing", {"room": ROOM, "is_typing": False})
    assert _by_name(bob.get_received())["chat:typing:stop"]["user_id"] == "alice"


def test_presence_list_on_join(server) -> None:
    app, socketio, _ = server
    alice = _client(app, socketio, "alice")
    alice.emit("join", {"room": ROOM})
    alice.get_received()

    bob = _client(app, socketio, "bob")
    bob.emit("join", {"room": ROOM})
    # alice should receive a presence:list for the room naming both users
    lists = _all(alice.get_received(), "presence:list")
    assert lists, "expected a presence:list broadcast"
    latest_room_list = [pl for pl in lists if pl["room"] == ROOM][-1]
    assert {u["user_id"] for u in latest_room_list["users"]} == {"alice", "bob"}


def test_disconnect_marks_offline(server) -> None:
    app, socketio, chat = server
    alice = _client(app, socketio, "alice")
    bob = _client(app, socketio, "bob")
    for c in (alice, bob):
        c.emit("join", {"room": ROOM})
        c.get_received()

    alice.disconnect()
    presence = _all(bob.get_received(), "presence:update")
    assert any(p == {"user_id": "alice", "status": "offline"} for p in presence)
    assert chat.registry.is_online("alice") is False
