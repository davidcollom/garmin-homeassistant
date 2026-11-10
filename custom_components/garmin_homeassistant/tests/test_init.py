"""Tests for setting up the Garmin Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.garmin_homeassistant.const import DOMAIN


async def test_setup_entry_creates_the_watch_entities(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The sensors of a paired watch are created."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    states = hass.states.async_all()
    entity_ids = {state.entity_id for state in states}
    assert "sensor.edge_1040_battery" in entity_ids
    assert "sensor.edge_1040_steps" in entity_ids
    assert "sensor.edge_1040_heart_rate" in entity_ids
    assert "binary_sensor.edge_1040_connected" in entity_ids


async def test_setup_entry_registers_a_device(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The watch shows up as a device."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, "edge1040-1")})
    assert device is not None
    assert device.manufacturer == "Garmin"
    assert device.model == "282x470"


async def test_setup_entry_registers_the_services(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The integration services are available."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "send_notification")
    assert hass.services.has_service(DOMAIN, "run_command")
    assert hass.services.has_service(DOMAIN, "set_exposed_entities")
    assert hass.services.has_service(DOMAIN, "refresh")


async def test_setup_entry_registers_the_notify_service(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The notify platform is loaded through discovery."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service("notify", "garmin_homeassistant")


async def test_unload_entry(hass: HomeAssistant, mock_bridge, mock_config_entry) -> None:
    """The entry can be unloaded again."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.services.has_service(DOMAIN, "send_notification")


async def test_mirror_switches_are_created_when_enabled(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The optional mirror switches show the entities the watch can toggle."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={"create_mirror_switches": True}
    )

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)
    switch_ids = {entry.entity_id for entry in entries if entry.domain == "switch"}
    assert "switch.garmin_kitchen" in switch_ids
    # A lock only has the OPEN_CLOSE flag, but it can still be switched.
    assert "switch.garmin_front_door" in switch_ids


async def test_mirror_switches_are_not_created_by_default(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The mirror switches stay away when the option is off."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)
    assert not [entry for entry in entries if entry.domain == "switch"]
