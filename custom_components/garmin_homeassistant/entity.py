"""Base entity for the Garmin integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_WATCH_ID, DOMAIN
from .coordinator import GarminCoordinator


class GarminWatchEntity(CoordinatorEntity[GarminCoordinator]):
    """An entity that belongs to a specific paired watch."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: GarminCoordinator, watch: dict) -> None:
        """Initialise the entity for a watch."""
        super().__init__(coordinator)
        self._watch = watch
        self._watch_id = str(watch.get("watch_id", ""))
        self._attr_unique_id = f"{self._watch_id}_{self._attr_key}"

    @property
    def _attr_key(self) -> str:
        """Sub class specific key used to build the unique id."""
        return "base"

    @property
    def watch(self) -> dict:
        """The watch this entity belongs to."""
        return self._watch

    @property
    def watch_id(self) -> str:
        """Id of the paired watch."""
        return self._watch_id

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the watch as a Home Assistant device."""
        name = str(self._watch.get("name") or "Garmin Watch")
        model = str(self._watch.get("model") or "")
        return DeviceInfo(
            identifiers={(DOMAIN, self._watch_id)},
            name=name,
            model=model or None,
            manufacturer="Garmin",
            sw_version=str(self._watch.get("api_level") or "") or None,
        )

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Common watch attributes."""
        attributes: dict[str, object] = {ATTR_WATCH_ID: self._watch_id}
        for key in ("model", "api_level", "last_seen", "steps", "heart_rate"):
            if self._watch.get(key) is not None:
                attributes[key] = self._watch[key]
        return attributes
