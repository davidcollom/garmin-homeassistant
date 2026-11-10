"""Binary sensor platform for the Garmin integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback

from . import GarminConfigEntry
from .compat import AddConfigEntryEntitiesCallback
from .coordinator import GarminCoordinator
from .entity import GarminWatchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the watch connectivity sensors."""
    coordinator: GarminCoordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new_entities: list[GarminWatchConnectedSensor] = []
        for watch in coordinator.data.watches:
            watch_id = str(watch.get("watch_id", ""))
            if watch_id in known:
                continue
            known.add(watch_id)
            new_entities.append(GarminWatchConnectedSensor(coordinator, watch))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))
    _async_add_new()


class GarminWatchConnectedSensor(GarminWatchEntity, BinarySensorEntity):
    """Reports whether a watch has recently talked to the bridge."""

    _attr_name = "Connected"
    _attr_icon = "mdi:watch"

    def __init__(self, coordinator: GarminCoordinator, watch: dict[str, Any]) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, watch)

    @property
    def _attr_key(self) -> str:
        """Unique key for this sensor."""
        return "connected"

    @property
    def is_on(self) -> bool | None:
        """True when the watch was seen recently."""
        for watch in self.coordinator.data.watches:
            if str(watch.get("watch_id")) == self.watch_id:
                last_seen = watch.get("last_seen")
                if not last_seen:
                    return False
                return _is_recent(last_seen)
        return None

    @property
    def available(self) -> bool:
        """The sensor is available as long as the watch is known."""
        return any(
            str(watch.get("watch_id")) == self.watch_id for watch in self.coordinator.data.watches
        )


def _is_recent(last_seen: Any, window: int = 900) -> bool:
    """Return True when the timestamp is within the stale window."""
    import time

    try:
        return (time.time() - float(last_seen)) < window
    except (TypeError, ValueError):
        return False
