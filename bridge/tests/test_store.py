"""Tests for the in-memory stores of the bridge."""

from __future__ import annotations

from garmin_bridge.models import NotificationAction
from garmin_bridge.store import EntityStore, NotificationQueue, WatchRegistry


def _state(entity_id: str, state: str, attributes: dict | None = None) -> dict:
    return {"entity_id": entity_id, "state": state, "attributes": attributes or {}}


def test_sync_populates_the_mirror() -> None:
    store = EntityStore()
    changed = store.sync(
        {
            "light.kitchen": _state("light.kitchen", "on", {"friendly_name": "Kitchen"}),
            "lock.front": _state("lock.front", "locked"),
        },
        {"light.kitchen": "Kitchen"},
    )

    assert changed == 2
    assert store.revision == 1
    assert len(store.all_entities()) == 2

    kitchen = store.entity("light.kitchen")
    assert kitchen is not None
    assert kitchen.n == "Kitchen"
    assert kitchen.d == "light"
    assert kitchen.a == 0


def test_uncontrollable_domains_are_skipped() -> None:
    store = EntityStore()
    store.sync(
        {
            "sensor.temperature": _state("sensor.temperature", "21.5"),
            "light.kitchen": _state("light.kitchen", "on"),
        },
        {},
    )

    assert [entity.i for entity in store.all_entities()] == ["light.kitchen"]


def test_allow_and_block_lists_are_applied() -> None:
    store = EntityStore()
    store.sync(
        {
            "light.a": _state("light.a", "on"),
            "light.b": _state("light.b", "on"),
            "light.c": _state("light.c", "on"),
        },
        {},
        allowlist=["light.a", "light.b"],
        blocklist=["light.b"],
    )

    assert [entity.i for entity in store.all_entities()] == ["light.a"]


def test_revision_only_moves_when_something_changes() -> None:
    store = EntityStore()
    states = {"light.a": _state("light.a", "on")}
    store.sync(states, {})
    assert store.revision == 1

    store.sync(dict(states), {})
    assert store.revision == 1

    store.sync({"light.a": _state("light.a", "off")}, {})
    assert store.revision == 2


def test_changed_since_reports_updates() -> None:
    store = EntityStore()
    store.sync({"light.a": _state("light.a", "on")}, {})
    first = store.revision

    store.sync({"light.a": _state("light.a", "off")}, {})

    assert store.changed_since(first) == ["light.a"]
    assert store.changed_since(store.revision) == []


def test_removed_since_reports_deletions() -> None:
    store = EntityStore()
    store.sync(
        {"light.a": _state("light.a", "on"), "light.b": _state("light.b", "on")},
        {},
    )
    first = store.revision

    store.sync({"light.a": _state("light.a", "on")}, {})

    assert store.removed_since(first) == ["light.b"]
    assert store.changed_since(first) == []


def test_snapshot_pages_through_the_entities() -> None:
    store = EntityStore()
    store.sync(
        {f"light.l{index}": _state(f"light.l{index}", "on") for index in range(10)},
        {},
    )

    first = store.snapshot(limit=4, offset=0)
    assert len(first.e) == 4
    assert first.n == 10
    assert first.more is True

    last = store.snapshot(limit=4, offset=8)
    assert len(last.e) == 2
    assert last.more is False


def test_snapshot_reports_removed_entities() -> None:
    store = EntityStore()
    snapshot = store.snapshot(removed=["light.gone"])
    assert snapshot.r == ["light.gone"]


def test_watch_registry_issues_a_stable_token() -> None:
    registry = WatchRegistry()
    registry.register("watch-1", "Garmin", model="282x470", api_level=600)

    token = registry.issue_token("watch-1")
    assert token
    assert registry.issue_token("watch-1") == token
    assert registry.token("watch-1") == token
    assert registry.token("watch-2") is None


def test_watch_registry_tracks_telemetry() -> None:
    registry = WatchRegistry()
    registry.register("watch-1", "Garmin")

    registry.update_telemetry("watch-1", battery=55, steps=1234, heart_rate=60)
    watch = registry.all()[0]

    assert watch.battery == 55
    assert watch.steps == 1234
    assert watch.heart_rate == 60


def test_notification_queue_round_trip() -> None:
    queue = NotificationQueue()
    queue.ensure_watch("watch-1")

    created = queue.publish(
        title="Doorbell",
        body="Someone is at the door",
        actions=[NotificationAction(id="open", label="Open")],
        entity_id="binary_sensor.doorbell",
    )

    assert len(created) == 1
    pending = queue.pending("watch-1")
    assert len(pending) == 1
    assert pending[0].title == "Doorbell"
    assert pending[0].actions[0].label == "Open"

    assert queue.acknowledge("watch-1", pending[0].id, "open") is True
    assert queue.pending("watch-1") == []
    assert queue.acknowledge("watch-1", "nope") is False


def test_notification_cursor_advances() -> None:
    queue = NotificationQueue()
    queue.ensure_watch("watch-1")
    assert queue.cursor("watch-1") == 0

    queue.publish(title="One", watch_ids=["watch-1"])
    assert queue.cursor("watch-1") == 1
