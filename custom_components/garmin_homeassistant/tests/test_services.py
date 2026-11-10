"""Tests for the services of the Garmin integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.garmin_homeassistant.const import (
    DOMAIN,
    SERVICE_REFRESH,
    SERVICE_RUN_COMMAND,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_SET_EXPOSED_ENTITIES,
)


async def _setup(hass: HomeAssistant, mock_config_entry) -> None:
    """Set up the integration."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


def _calls_to(mock, path: str) -> list:
    """Return the recorded calls for one path of the bridge."""
    return [call for call in mock.mock_calls if str(call[1]).endswith(path)]


async def test_send_notification_queues_a_message(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The service forwards the message to the bridge."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_NOTIFICATION,
        {"message": "Doorbell", "title": "Front door", "priority": "high"},
        blocking=True,
    )

    calls = _calls_to(mock_bridge, "/v1/admin/notify")
    assert len(calls) == 1
    _method, _url, payload, _headers = calls[0]
    assert payload == {
        "title": "Front door",
        "body": "Doorbell",
        "priority": "high",
    }


async def test_run_command_answers_with_the_result(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The command service returns what the bridge answered."""
    await _setup(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_RUN_COMMAND,
        {"command": "toggle", "entity_id": "light.kitchen"},
        blocking=True,
        return_response=True,
    )

    assert response == {"ok": True, "message": "light.turn_on"}

    calls = _calls_to(mock_bridge, "/v1/commands")
    assert len(calls) == 1
    _method, _url, payload, _headers = calls[0]
    assert payload == {"cmd": "toggle", "data": {}, "entity_id": "light.kitchen"}


async def test_set_exposed_entities_updates_the_bridge(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The exposure list is pushed to the bridge and stored."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_EXPOSED_ENTITIES,
        {"entity_ids": ["light.kitchen", "lock.front_door"]},
        blocking=True,
    )
    await hass.async_block_till_done()

    calls = _calls_to(mock_bridge, "/v1/admin/config")
    assert calls
    _method, _url, payload, _headers = calls[-1]
    assert payload["exposed_entities"] == ["light.kitchen", "lock.front_door"]
    assert mock_config_entry.options["exposed_entities"] == [
        "light.kitchen",
        "lock.front_door",
    ]


async def test_refresh_asks_the_bridge_to_resync(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The refresh service triggers a resync."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)

    assert len(_calls_to(mock_bridge, "/v1/admin/refresh")) == 1


async def test_the_services_use_the_configured_bridge(
    hass: HomeAssistant, mock_bridge, mock_config_entry, bridge_url
) -> None:
    """The bridge URL of the config entry is used."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)

    for _method, url, _payload, _headers in mock_bridge.mock_calls:
        assert str(url).startswith(bridge_url)
