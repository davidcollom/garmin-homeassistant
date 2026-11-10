"""Switch platform mirroring the entities exposed to the watches.

These switches are optional.  They give Home Assistant a native handle on the
same entities the watch can control, which is handy for dashboards and for
automations that want to know what the watch is allowed to see.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GarminConfigEntry
from .compat import AddConfigEntryEntitiesCallback
from .const import CONF_CREATE_MIRROR_SWITCHES, FLAG_OPEN_CLOSE, FLAG_TOGGLE
from .coordinator import GarminCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mirror switches when the option is enabled."""
    if not entry.options.get(CONF_CREATE_MIRROR_SWITCHES, False):
        return

    coordinator: GarminCoordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new_entities: list[GarminMirrorSwitch] = []
        for entity in coordinator.data.entities:
            entity_id = str(entity.get("entity_id", ""))
            if not entity_id or entity_id in known:
                continue
            flags = int(entity.get("flags") or 0)
            if not flags & (FLAG_TOGGLE | FLAG_OPEN_CLOSE):
                continue
            known.add(entity_id)
            new_entities.append(GarminMirrorSwitch(coordinator, entity))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))
    _async_add_new()


class GarminMirrorSwitch(CoordinatorEntity[GarminCoordinator], SwitchEntity):
    """A switch that proxies a Home Assistant entity through the bridge."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator: GarminCoordinator, entity: dict[str, Any]) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._entity_id = str(entity.get("entity_id", ""))
        name = str(entity.get("name") or self._entity_id)
        self._attr_name = f"Garmin {name}"
        self._attr_unique_id = f"mirror_{self._entity_id}"
        self._attr_icon = "mdi:watch"

    @property
    def _current(self) -> dict[str, Any] | None:
        """The current state of the mirrored entity."""
        for entity in self.coordinator.data.entities:
            if str(entity.get("entity_id")) == self._entity_id:
                return entity
        return None

    @property
    def is_on(self) -> bool | None:
        """Return the state of the mirrored entity."""
        entity = self._current
        if entity is None:
            return None
        return str(entity.get("state", "")).lower() in {"on", "open", "playing", "home", "locked"}

    @property
    def available(self) -> bool:
        """The switch is available while the entity exists."""
        return self._current is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the mirrored entity on."""
        await self.coordinator.client.async_command("turn_on", self._entity_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the mirrored entity off."""
        await self.coordinator.client.async_command("turn_off", self._entity_id)
        await self.coordinator.async_request_refresh()
