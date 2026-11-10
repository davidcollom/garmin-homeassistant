"""Sensor platform for the Garmin integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback

from . import GarminConfigEntry
from .compat import AddConfigEntryEntitiesCallback
from .const import DOMAIN
from .coordinator import GarminCoordinator
from .entity import GarminWatchEntity


@dataclass(frozen=True, kw_only=True)
class GarminSensorDescription(SensorEntityDescription):
    """Describes a Garmin watch sensor.

    The description extends the Home Assistant one with a ``value`` callable
    that extracts the reading of a watch from the coordinator data.
    """

    value: Callable[[dict[str, Any]], Any] = lambda watch: watch.get("battery")


def _last_seen(watch: dict[str, Any]) -> datetime | None:
    """Return the moment the watch was last seen as a datetime."""
    value = watch.get("last_seen")
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (OSError, OverflowError, TypeError, ValueError):
        return None


SENSOR_DESCRIPTIONS: tuple[GarminSensorDescription, ...] = (
    GarminSensorDescription(
        key="battery",
        name="Battery",
        icon="mdi:battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        value=lambda watch: watch.get("battery"),
    ),
    GarminSensorDescription(
        key="steps",
        name="Steps",
        icon="mdi:walk",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="steps",
        value=lambda watch: watch.get("steps"),
    ),
    GarminSensorDescription(
        key="heart_rate",
        name="Heart rate",
        icon="mdi:heart",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="bpm",
        value=lambda watch: watch.get("heart_rate"),
    ),
    GarminSensorDescription(
        key="last_seen",
        name="Last seen",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=_last_seen,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the watch sensors."""
    coordinator: GarminCoordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _async_add_new() -> None:
        new_entities: list[GarminWatchSensor] = []
        for watch in coordinator.data.watches:
            watch_id = str(watch.get("watch_id", ""))
            for description in SENSOR_DESCRIPTIONS:
                key = f"{watch_id}_{description.key}"
                if key in known:
                    continue
                known.add(key)
                new_entities.append(GarminWatchSensor(coordinator, watch, description))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new))
    _async_add_new()


class GarminWatchSensor(GarminWatchEntity, SensorEntity):
    """A sensor reporting a value from a paired watch."""

    entity_description: GarminSensorDescription

    def __init__(
        self,
        coordinator: GarminCoordinator,
        watch: dict[str, Any],
        description: GarminSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        self.entity_description = description
        super().__init__(coordinator, watch)

    @property
    def _attr_key(self) -> str:
        """Unique key for this sensor."""
        return self.entity_description.key

    @property
    def native_value(self) -> Any:
        """Return the current value from the coordinator data."""
        for watch in self.coordinator.data.watches:
            if str(watch.get("watch_id")) == self.watch_id:
                return self.entity_description.value(watch)
        return None

    @property
    def available(self) -> bool:
        """The sensor is available while the watch is known."""
        return self.native_value is not None


async def async_setup(hass: HomeAssistant, config: Any) -> bool:
    """Set up the sensor platform from yaml (not supported)."""
    return True


__all__ = ["DOMAIN", "async_setup_entry"]
