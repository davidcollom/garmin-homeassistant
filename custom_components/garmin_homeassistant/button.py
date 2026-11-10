"""Button platform for the Garmin integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback

from . import GarminConfigEntry
from .compat import AddConfigEntryEntitiesCallback
from .const import DEFAULT_NOTIFY_TITLE
from .coordinator import GarminCoordinator
from .entity import GarminWatchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the per watch buttons."""
    coordinator: GarminCoordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new_entities: list[GarminWatchTestNotificationButton] = []
        for watch in coordinator.data.watches:
            watch_id = str(watch.get("watch_id", ""))
            if watch_id in known:
                continue
            known.add(watch_id)
            new_entities.append(GarminWatchTestNotificationButton(coordinator, watch))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))
    _async_add_new()


class GarminWatchTestNotificationButton(GarminWatchEntity, ButtonEntity):
    """Sends a test notification to a specific watch."""

    _attr_name = "Test notification"
    _attr_icon = "mdi:message-alert"

    def __init__(self, coordinator: GarminCoordinator, watch: dict[str, Any]) -> None:
        """Initialise the button."""
        super().__init__(coordinator, watch)

    @property
    def _attr_key(self) -> str:
        """Unique key for this button."""
        return "test_notification"

    async def async_press(self) -> None:
        """Send a test notification to this watch."""
        await self.coordinator.client.async_notify(
            title=DEFAULT_NOTIFY_TITLE,
            message=f"Hello from {self._watch.get('name') or 'your Garmin watch'}",
            priority="normal",
            watch_ids=[self.watch_id],
        )
