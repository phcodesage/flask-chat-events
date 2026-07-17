"""Unit tests for the message store."""

from __future__ import annotations

import pytest

from flask_chat_events import InMemoryMessageStore


def _msg(mid: str, text: str = "hi", room: str = "general") -> dict:
    return {"id": mid, "room": room, "user_id": "u", "text": text}


def test_add_and_history_oldest_first() -> None:
    store = InMemoryMessageStore()
    store.add("general", _msg("1", "a"))
    store.add("general", _msg("2", "b"))
    history = store.history("general")
    assert [m["text"] for m in history] == ["a", "b"]


def test_history_unknown_room_is_empty() -> None:
    assert InMemoryMessageStore().history("nope") == []


def test_history_limit_returns_most_recent() -> None:
    store = InMemoryMessageStore()
    for i in range(5):
        store.add("general", _msg(str(i)))
    assert [m["id"] for m in store.history("general", limit=2)] == ["3", "4"]


def test_max_per_room_caps_and_drops_oldest() -> None:
    store = InMemoryMessageStore(max_per_room=3)
    for i in range(5):
        store.add("general", _msg(str(i)))
    assert [m["id"] for m in store.history("general")] == ["2", "3", "4"]


def test_max_per_room_must_be_positive() -> None:
    with pytest.raises(ValueError):
        InMemoryMessageStore(max_per_room=0)


def test_get_returns_copy() -> None:
    store = InMemoryMessageStore()
    store.add("general", _msg("1", "a"))
    got = store.get("general", "1")
    assert got is not None and got["text"] == "a"
    got["text"] = "mutated"
    assert store.get("general", "1")["text"] == "a"  # store not affected


def test_get_missing_returns_none() -> None:
    assert InMemoryMessageStore().get("general", "x") is None


def test_edit_updates_text_and_sets_edited_at() -> None:
    store = InMemoryMessageStore()
    store.add("general", _msg("1", "old"))
    updated = store.edit("general", "1", "new", edited_at="2020-01-01T00:00:00+00:00")
    assert updated is not None
    assert updated["text"] == "new"
    assert updated["edited_at"] == "2020-01-01T00:00:00+00:00"
    assert store.get("general", "1")["text"] == "new"


def test_edit_missing_returns_none() -> None:
    assert InMemoryMessageStore().edit("g", "x", "t", edited_at="t") is None


def test_delete_removes_message() -> None:
    store = InMemoryMessageStore()
    store.add("general", _msg("1"))
    store.add("general", _msg("2"))
    assert store.delete("general", "1") is True
    assert [m["id"] for m in store.history("general")] == ["2"]


def test_delete_missing_returns_false() -> None:
    store = InMemoryMessageStore()
    store.add("general", _msg("1"))
    assert store.delete("general", "x") is False


def test_clear_room_and_all() -> None:
    store = InMemoryMessageStore()
    store.add("a", _msg("1"))
    store.add("b", _msg("2"))
    store.clear("a")
    assert store.history("a") == []
    assert store.history("b") != []
    store.clear()
    assert store.history("b") == []


def test_stored_message_is_decoupled_from_caller() -> None:
    store = InMemoryMessageStore()
    original = _msg("1", "a")
    store.add("general", original)
    original["text"] = "mutated after add"
    assert store.history("general")[0]["text"] == "a"
