"""Data coordinator for the Garmin bridge integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BridgeClient, BridgeError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class GarminData:
    """Snapshot of everything the integration needs."""

    watches: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)

    @property
    def watch_ids(self) -> set[str]:
        """Ids of the known watches."""
        return {str(watch.get("watch_id")) for watch in self.watches}


class GarminCoordinator(DataUpdateCoordinator[GarminData]):
    """Polls the bridge for watch and entity state."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, client: BridgeClient, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_interval(entry),
        )
        self.client = client

    async def _async_update_data(self) -> GarminData:
        """Fetch the latest data from the bridge."""
        try:
            watches = await self.client.async_watches()
            entities = await self.client.async_entities()
        except BridgeError as err:
            raise UpdateFailed(f"Could not talk to the Garmin bridge: {err}") from err
        return GarminData(watches=watches, entities=entities)


def _interval(entry: ConfigEntry) -> Any:
    """Return the configured update interval."""
    from datetime import timedelta

    seconds = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = DEFAULT_SCAN_INTERVAL
    return timedelta(seconds=max(5, seconds))
