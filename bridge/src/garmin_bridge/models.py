"""Wire models for the bridge API.

The watch-facing payloads are intentionally compact: they travel over BLE to
the phone and then over the mobile network, so every byte counts.  The
verbose variants exist for the Home Assistant integration and for debugging.
"""

from __future__ import annotations

from enum import IntFlag
from typing import Any, Literal

from pydantic import BaseModel, Field, field_serializer

# ---------------------------------------------------------------------------
# Compact entity encoding
# ---------------------------------------------------------------------------


class EntityFlags(IntFlag):
    """Bit flags describing what a watch can do with an entity."""

    NONE = 0
    #: Entity supports a simple on/off toggle.
    TOGGLE = 1
    #: Entity has a brightness attribute (light).
    BRIGHTNESS = 2
    #: Entity has a numeric level/setpoint attribute.
    LEVEL = 4
    #: Entity supports open/close rather than on/off (locks, covers).
    OPEN_CLOSE = 8
    #: Entity supports a target temperature / mode (climate).
    SETPOINT = 16
    #: Entity is pinned to the top of the watch list.
    PINNED = 32
    #: Entity exposes a numeric percentage (battery, humidity).
    PERCENT = 64


class CompactEntity(BaseModel):
    """Compact representation of a Home Assistant entity.

    The watch renders a list of these.  Field names are short because the
    payload is serialised once per poll for every paired watch.
    """

    #: Home Assistant entity id, e.g. ``light.kitchen``.
    i: str
    #: Human readable name.
    n: str
    #: Home Assistant domain, e.g. ``light``.
    d: str
    #: Normalised state string.
    s: str
    #: Bit flags from :class:`EntityFlags`.
    f: int = 0
    #: Index into the ``areas`` table, or ``-1`` when the entity has no area.
    a: int = -1
    #: Optional numeric attribute (brightness, percentage, setpoint).
    v: float | None = None


class EntitySnapshot(BaseModel):
    """A point-in-time view of the controllable entities."""

    #: Unix timestamp of the snapshot.
    ts: int
    #: Monotonic revision; bump whenever any entity changes.
    rev: int
    #: Known area names, indexed by :attr:`CompactEntity.a`.
    areas: list[str] = Field(default_factory=list)
    #: Compact entity rows.
    e: list[CompactEntity] = Field(default_factory=list)
    #: Entity ids that disappeared since the revision the watch sent.
    r: list[str] = Field(default_factory=list)
    #: Total number of entities the bridge knows about.
    n: int = 0
    #: True when more entities are available beyond this page.
    more: bool = False

    @field_serializer("e")
    def _serialize_entities(self, entities: list[CompactEntity]) -> list[list[Any]]:
        """Serialise the entities as flat arrays.

        The watch parses the rows positionally, so the field names would be
        pure overhead: a seven element array is roughly a third of the size
        of the equivalent JSON object.
        """
        return [[e.i, e.n, e.d, e.s, e.f, e.a, e.v] for e in entities]


class VerboseEntity(BaseModel):
    """Human friendly entity representation used by the admin API."""

    entity_id: str
    name: str
    domain: str
    state: str
    area: str | None = None
    flags: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class CommandRequest(BaseModel):
    """A command sent from a watch to Home Assistant."""

    #: ``toggle``, ``turn_on``, ``turn_off``, ``open``, ``close``,
    #: ``set_level``, ``set_value`` or ``service``.
    cmd: str
    #: Target entity id.
    entity_id: str | None = None
    #: Service payload for ``cmd == "service"``.
    data: dict[str, Any] = Field(default_factory=dict)
    #: Optional explicit service name for ``cmd == "service"``.
    service: str | None = None
    #: Optional domain for ``cmd == "service"`` (defaults to the entity domain).
    domain: str | None = None


class CommandResponse(BaseModel):
    """Result of a command."""

    ok: bool
    #: Human readable message, always safe to show on a watch.
    message: str = ""
    #: The resulting entity state when known.
    state: str | None = None


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class NotificationAction(BaseModel):
    """An action the user can pick directly on the watch notification."""

    id: str
    label: str


class WatchNotification(BaseModel):
    """A notification queued for a watch."""

    id: str
    ts: int
    title: str
    body: str = ""
    #: ``low`` | ``normal`` | ``high``.
    priority: Literal["low", "normal", "high"] = "normal"
    #: Optional actions rendered as buttons on the watch.
    actions: list[NotificationAction] = Field(default_factory=list)
    #: Optional entity the notification relates to.
    entity_id: str | None = None
    #: True once the watch has acknowledged the notification.
    ack: bool = False


class NotificationList(BaseModel):
    """Response to ``GET /v1/notifications``."""

    ts: int
    #: Cursor to pass back as ``since`` on the next poll.
    cursor: int
    n: list[WatchNotification] = Field(default_factory=list)

    @field_serializer("n")
    def _serialize_notifications(self, notifications: list[WatchNotification]) -> list[list[Any]]:
        """Serialise the notifications as flat arrays.

        The layout mirrors :class:`EntitySnapshot`: the watch reads the
        columns positionally.
        """
        return [
            [
                n.id,
                n.ts,
                n.title,
                n.body,
                n.priority,
                [[a.id, a.label] for a in n.actions],
                n.entity_id,
            ]
            for n in notifications
        ]


class NotificationAck(BaseModel):
    """Acknowledgement payload sent by a watch."""

    action: str | None = None


# ---------------------------------------------------------------------------
# Watch telemetry / events
# ---------------------------------------------------------------------------


class WatchEvent(BaseModel):
    """An event sent from a watch to the bridge."""

    type: Literal["telemetry", "button", "ping", "error"] = "telemetry"
    ts: int = 0
    #: Battery percentage 0-100.
    battery: int | None = None
    #: Step count.
    steps: int | None = None
    #: Heart rate in bpm.
    heart_rate: int | None = None
    #: Identifier of the button that was pressed.
    button: str | None = None
    #: Free-form text for error events.
    message: str | None = None


class WatchRegistration(BaseModel):
    """Registration payload sent the first time a watch connects."""

    #: Stable identifier generated by the watch app.
    watch_id: str
    name: str = "Garmin"
    #: CIQ product id, e.g. ``venu4``.
    model: str = ""
    #: CIQ API level reported by the watch.
    api_level: int = 0
    #: Capabilities advertised by the watch app.
    capabilities: dict[str, bool] = Field(default_factory=dict)


class WatchInfo(BaseModel):
    """Information about a paired watch."""

    watch_id: str
    name: str
    model: str = ""
    api_level: int = 0
    capabilities: dict[str, bool] = Field(default_factory=dict)
    #: Unix timestamp of the last request seen for this watch.
    last_seen: int = 0
    battery: int | None = None
    steps: int | None = None
    heart_rate: int | None = None


class WatchList(BaseModel):
    """Response to ``GET /v1/watches``."""

    watches: list[WatchInfo] = Field(default_factory=list)


class WatchRegistrationResponse(WatchInfo):
    """Response to ``POST /v1/watches/register``.

    The bridge hands out a token that is bound to this watch.  The watch
    stores it and uses it for every later request, so the shared bootstrap
    token only has to be configured once.
    """

    #: Token bound to this watch.
    token: str = ""


class HealthResponse(BaseModel):
    """Response to ``GET /v1/health``."""

    ok: bool
    version: str
    #: Seconds since the bridge last successfully synced with Home Assistant.
    ha_connected: bool = False
    entities: int = 0
    watches: int = 0


class WatchConfig(BaseModel):
    """Server supplied watch settings."""

    #: Seconds the watch should wait between foreground polls.
    poll_interval: int = 15
    #: Seconds between background polls.
    background_interval: int = 900
    #: Maximum number of entities to request in one page.
    page_size: int = 25
    #: Optional server-side notice shown on the watch home screen.
    message: str = ""
