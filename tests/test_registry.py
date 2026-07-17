"""Unit tests for the presence registry."""

from __future__ import annotations

from flask_chat_events import PresenceRegistry


def test_connect_and_online_users() -> None:
    reg = PresenceRegistry()
    reg.connect("sid1", "alice", avatar_color="#fff")
    users = reg.online_users()
    assert users == [{"user_id": "alice", "avatar_color": "#fff"}]
    assert reg.is_online("alice") is True
    assert reg.is_online("bob") is False


def test_user_for() -> None:
    reg = PresenceRegistry()
    reg.connect("sid1", "alice")
    assert reg.user_for("sid1") == "alice"
    assert reg.user_for("nope") is None


def test_join_leave_and_users_in() -> None:
    reg = PresenceRegistry()
    reg.connect("sid1", "alice")
    reg.connect("sid2", "bob")
    reg.join("sid1", "general")
    reg.join("sid2", "general")
    reg.join("sid2", "random")

    assert {u["user_id"] for u in reg.users_in("general")} == {"alice", "bob"}
    assert {u["user_id"] for u in reg.users_in("random")} == {"bob"}

    reg.leave("sid2", "general")
    assert {u["user_id"] for u in reg.users_in("general")} == {"alice"}
    assert reg.rooms_for("sid2") == {"random"}


def test_multiple_connections_dedup_by_user() -> None:
    reg = PresenceRegistry()
    reg.connect("sid1", "alice")
    reg.connect("sid2", "alice")  # second tab
    assert reg.online_users() == [{"user_id": "alice"}]


def test_disconnect_reports_was_last() -> None:
    reg = PresenceRegistry()
    reg.connect("sid1", "alice")
    reg.connect("sid2", "alice")
    reg.join("sid1", "general")

    info = reg.disconnect("sid1")
    assert info is not None
    assert info["user_id"] == "alice"
    assert info["rooms"] == {"general"}
    assert info["was_last"] is False  # sid2 still connected
    assert reg.is_online("alice") is True

    info2 = reg.disconnect("sid2")
    assert info2["was_last"] is True
    assert reg.is_online("alice") is False


def test_disconnect_unknown_returns_none() -> None:
    assert PresenceRegistry().disconnect("ghost") is None
