"""In-memory state: entity mirror, watch registry and notification queues.

Everything lives in RAM.  The bridge is a cache in front of Home Assistant,
so a restart simply re-syncs and watches re-register on their next poll.
"""

from __future__ import annotations

import logging
import secrets
import time
from collections import deque
from collections.abc import Iterable
from typing import Any

from .ha import HomeAssistantClient
from .models import (
    CompactEntity,
    EntitySnapshot,
    NotificationAction,
    WatchInfo,
    WatchNotification,
)

_LOGGER = logging.getLogger(__name__)

#: How many entity revisions are remembered for incremental polling.
CHANGE_LOG_LIMIT = 500

#: How many notifications are retained per watch.
NOTIFICATION_LIMIT = 50


def _now() -> int:
    return int(time.time())


class EntityStore:
    """A compact, revisioned mirror of the Home Assistant entity states."""

    def __init__(self) -> None:
        self._entities: dict[str, CompactEntity] = {}
        self._areas: list[str] = []
        self._area_index: dict[str, int] = {}
        self._revision = 0
        # (revision, entity id, still present)
        self._changes: deque[tuple[int, str, bool]] = deque(maxlen=CHANGE_LOG_LIMIT)
        self._entity_revision: dict[str, int] = {}

    # -- syncing -----------------------------------------------------------

    def sync(
        self,
        states: dict[str, dict[str, Any]],
        areas: dict[str, str],
        allowlist: Iterable[str] | None = None,
        blocklist: Iterable[str] = (),
    ) -> int:
        """Rebuild the mirror from a Home Assistant state snapshot.

        ``allowlist`` limits the entities that are mirrored.  ``None`` means
        that there is no limit, an empty collection means that nothing is
        mirrored.  The entries of ``blocklist`` are never mirrored.

        Returns the number of entities that changed since the previous sync.
        """
        allow = None if allowlist is None else set(allowlist)
        block = set(blocklist)

        area_names: list[str] = []
        area_lookup: dict[str, int] = {}
        for area in areas.values():
            if area not in area_lookup:
                area_lookup[area] = len(area_names)
                area_names.append(area)

        new_entities: dict[str, CompactEntity] = {}
        for entity_id, state in states.items():
            domain = entity_id.split(".", 1)[0]
            if not HomeAssistantClient.is_exposed(domain):
                continue
            if allow is not None and entity_id not in allow:
                continue
            if entity_id in block:
                continue

            attributes = state.get("attributes") or {}
            name = attributes.get("friendly_name") or entity_id
            area_name = areas.get(entity_id)
            area_idx = area_lookup.get(area_name, -1) if area_name else -1

            new_entities[entity_id] = CompactEntity(
                i=entity_id,
                n=str(name),
                d=domain,
                s=str(state.get("state", "unknown")),
                f=HomeAssistantClient.entity_flags(state),
                a=area_idx,
                v=HomeAssistantClient.entity_value(state),
            )

        changed_ids: list[str] = []
        for entity_id, entity in new_entities.items():
            previous = self._entities.get(entity_id)
            if previous is None or previous != entity:
                changed_ids.append(entity_id)

        removed = set(self._entities) - set(new_entities)
        changed = len(changed_ids) + len(removed)

        self._entities = new_entities
        self._areas = area_names
        self._area_index = area_lookup

        if changed:
            self._revision += 1
            for entity_id in changed_ids:
                self._changes.append((self._revision, entity_id, True))
                self._entity_revision[entity_id] = self._revision
            for entity_id in removed:
                self._changes.append((self._revision, entity_id, False))
                self._entity_revision.pop(entity_id, None)

        return changed

    # -- reading -----------------------------------------------------------

    @property
    def revision(self) -> int:
        """Current revision; incremented whenever any entity changes."""
        return self._revision

    def snapshot(
        self,
        entity_ids: Iterable[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        removed: Iterable[str] = (),
    ) -> EntitySnapshot:
        """Return the current snapshot, optionally limited to some entity ids.

        ``limit`` and ``offset`` page through the result set.  ``removed``
        carries the entity ids that disappeared since the revision the watch
        sent, so that the watch can drop them from its local list.
        """
        if entity_ids is None:
            entities = list(self._entities.values())
        else:
            wanted = set(entity_ids)
            entities = [e for e in self._entities.values() if e.i in wanted]
        entities.sort(key=lambda e: (e.a if e.a >= 0 else 1 << 30, e.n.lower()))
        total = len(entities)
        more = False
        if limit is not None and limit >= 0:
            start = max(0, offset)
            page = entities[start : start + limit]
            more = (start + len(page)) < total
            entities = page
        return EntitySnapshot(
            ts=_now(),
            rev=self._revision,
            areas=list(self._areas),
            e=entities,
            r=list(removed),
            n=total,
            more=more,
        )

    def changed_since(self, revision: int) -> list[str]:
        """Entity ids that changed after ``revision``.

        When the change log no longer reaches back to ``revision`` every
        entity is reported so the caller resynchronises completely.
        """
        if revision >= self._revision:
            return []
        if not self._changes:
            return list(self._entities)
        oldest = min(rev for rev, _, _ in self._changes)
        if revision + 1 < oldest:
            return list(self._entities)
        seen: dict[str, None] = {}
        for rev, entity_id, present in self._changes:
            if rev > revision and present:
                seen[entity_id] = None
        return list(seen)

    def removed_since(self, revision: int) -> list[str]:
        """Entity ids that disappeared after ``revision``."""
        if revision >= self._revision:
            return []
        if not self._changes:
            return []
        oldest = min(rev for rev, _, _ in self._changes)
        if revision + 1 < oldest:
            # The watch is too far behind to know what disappeared.
            return []
        seen: dict[str, None] = {}
        for rev, entity_id, present in self._changes:
            if rev > revision and not present:
                seen[entity_id] = None
        return list(seen)

    def entity(self, entity_id: str) -> CompactEntity | None:
        """Look up a single entity."""
        return self._entities.get(entity_id)

    def all_entities(self) -> list[CompactEntity]:
        """All mirrored entities."""
        return list(self._entities.values())

    def verbose_entities(self) -> list[dict[str, Any]]:
        """Verbose entity dicts for the admin API."""
        result: list[dict[str, Any]] = []
        for entity in self._entities.values():
            area = self._areas[entity.a] if 0 <= entity.a < len(self._areas) else None
            result.append(
                {
                    "entity_id": entity.i,
                    "name": entity.n,
                    "domain": entity.d,
                    "state": entity.s,
                    "area": area,
                    "flags": entity.f,
                    "value": entity.v,
                }
            )
        return result


class WatchRegistry:
    """Tracks paired watches and their last reported telemetry."""

    def __init__(self, stale_after: int = 900) -> None:
        self._watches: dict[str, WatchInfo] = {}
        self._tokens: dict[str, str] = {}
        self._stale_after = stale_after

    def register(
        self,
        watch_id: str,
        name: str,
        model: str = "",
        api_level: int = 0,
        capabilities: dict[str, bool] | None = None,
    ) -> WatchInfo:
        """Register or refresh a watch."""
        existing = self._watches.get(watch_id)
        if existing is None:
            existing = WatchInfo(watch_id=watch_id, name=name)
            self._watches[watch_id] = existing
        existing.name = name or existing.name
        existing.model = model or existing.model
        existing.api_level = api_level or existing.api_level
        existing.capabilities = capabilities or existing.capabilities
        existing.last_seen = _now()
        return existing

    def issue_token(self, watch_id: str) -> str:
        """Return the token bound to a watch, creating one when needed.

        The token is handed out when the watch registers and lets the bridge
        recognise the watch without trusting the shared bootstrap token.
        """
        token = self._tokens.get(watch_id)
        if token is None:
            token = secrets.token_urlsafe(24)
            self._tokens[watch_id] = token
        return token

    def token(self, watch_id: str) -> str | None:
        """The token bound to a watch, if one was issued."""
        return self._tokens.get(watch_id)

    def touch(self, watch_id: str) -> WatchInfo | None:
        """Mark a watch as seen."""
        watch = self._watches.get(watch_id)
        if watch is None:
            return None
        watch.last_seen = _now()
        return watch

    def update_telemetry(
        self,
        watch_id: str,
        battery: int | None = None,
        steps: int | None = None,
        heart_rate: int | None = None,
    ) -> WatchInfo | None:
        """Store telemetry reported by a watch."""
        watch = self.touch(watch_id)
        if watch is None:
            return None
        if battery is not None:
            watch.battery = battery
        if steps is not None:
            watch.steps = steps
        if heart_rate is not None:
            watch.heart_rate = heart_rate
        return watch

    def all(self) -> list[WatchInfo]:
        """All known watches, newest first."""
        return sorted(self._watches.values(), key=lambda w: w.last_seen, reverse=True)

    def online(self) -> list[WatchInfo]:
        """Watches seen within the stale window."""
        cutoff = _now() - self._stale_after
        return [watch for watch in self.all() if watch.last_seen >= cutoff]

    def remove(self, watch_id: str) -> bool:
        """Forget a watch."""
        self._tokens.pop(watch_id, None)
        return self._watches.pop(watch_id, None) is not None


class NotificationQueue:
    """Per-watch notification queues with a monotonic cursor."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[WatchNotification]] = {}
        self._cursor = 0
        self._cursors: dict[str, int] = {}

    def _next_id(self) -> str:
        self._cursor += 1
        return f"n{self._cursor}"

    def cursor(self, watch_id: str) -> int:
        """Sequence number of the newest notification queued for a watch."""
        return self._cursors.get(watch_id, 0)

    def publish(
        self,
        title: str,
        body: str = "",
        priority: str = "normal",
        actions: list[NotificationAction] | None = None,
        entity_id: str | None = None,
        watch_ids: Iterable[str] | None = None,
    ) -> list[WatchNotification]:
        """Queue a notification for one or more watches.

        When ``watch_ids`` is ``None`` the notification is queued for every
        known watch, so it is picked up on their next poll.
        """
        targets = list(watch_ids) if watch_ids is not None else list(self._queues)
        if not targets:
            targets = []

        created: list[WatchNotification] = []
        for watch_id in targets:
            notification = WatchNotification(
                id=self._next_id(),
                ts=_now(),
                title=title,
                body=body,
                priority=priority,  # type: ignore[arg-type]
                actions=actions or [],
                entity_id=entity_id,
            )
            queue = self._queues.setdefault(watch_id, deque(maxlen=NOTIFICATION_LIMIT))
            queue.append(notification)
            self._cursors[watch_id] = self._cursor
            created.append(notification)
        return created

    def pending(self, watch_id: str) -> list[WatchNotification]:
        """Unacknowledged notifications for a watch."""
        queue = self._queues.get(watch_id)
        if not queue:
            return []
        return [n for n in queue if not n.ack]

    def acknowledge(self, watch_id: str, notification_id: str, action: str | None = None) -> bool:
        """Acknowledge a notification, optionally recording the chosen action."""
        queue = self._queues.get(watch_id)
        if not queue:
            return False
        for notification in queue:
            if notification.id == notification_id:
                notification.ack = True
                if action:
                    _LOGGER.info(
                        "Watch %s selected action %s on %s", watch_id, action, notification_id
                    )
                return True
        return False

    def notification(self, watch_id: str, notification_id: str) -> WatchNotification | None:
        """Return one notification of a watch."""
        queue = self._queues.get(watch_id)
        if not queue:
            return None
        for notification in queue:
            if notification.id == notification_id:
                return notification
        return None

    def watch_ids(self) -> list[str]:
        """Watch ids that have a queue."""
        return list(self._queues)

    def ensure_watch(self, watch_id: str) -> None:
        """Create an empty queue for a watch."""
        self._queues.setdefault(watch_id, deque(maxlen=NOTIFICATION_LIMIT))
