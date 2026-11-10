"""Tests for the Garmin notify platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.garmin_homeassistant.const import DOMAIN


async def _setup(hass: HomeAssistant, mock_config_entry) -> None:
    """Set up the integration."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_the_notify_service_is_registered(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The platform registers notify.garmin_homeassistant."""
    await _setup(hass, mock_config_entry)

    assert hass.services.has_service("notify", "garmin_homeassistant")


async def test_a_notification_is_queued_on_the_bridge(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The message ends up in the notification queue of the bridge."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        "notify",
        "garmin_homeassistant",
        {"message": "The washing machine has finished."},
        blocking=True,
    )

    calls = [call for call in mock_bridge.mock_calls if str(call[1]).endswith("/v1/admin/notify")]
    assert len(calls) == 1
    method, _url, payload, _headers = calls[0]
    assert method.lower() == "post"
    assert payload["body"] == "The washing machine has finished."
    assert payload["title"] == "Home Assistant"
    assert payload["priority"] == "normal"


async def test_a_notification_carries_the_title_and_the_actions(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The title, the actions and the target entity are forwarded."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        "notify",
        "garmin_homeassistant",
        {
            "message": "Front door",
            "title": "Doorbell",
            "data": {
                "priority": "high",
                "actions": [{"id": "open", "label": "Open"}],
                "entity_id": "lock.front_door",
            },
        },
        blocking=True,
    )

    calls = [call for call in mock_bridge.mock_calls if str(call[1]).endswith("/v1/admin/notify")]
    assert len(calls) == 1
    _method, _url, payload, _headers = calls[0]
    assert payload["title"] == "Doorbell"
    assert payload["priority"] == "high"
    assert payload["actions"] == [{"id": "open", "label": "Open"}]
    assert payload["entity_id"] == "lock.front_door"


async def test_a_notification_is_mirrored_to_the_phone(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The phone notification service receives a copy of the message."""
    received: list[dict] = []

    async def _handle(call) -> None:
        received.append(dict(call.data))

    hass.services.async_register("notify", "mobile_app_test", _handle)

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={"phone_notify_service": "mobile_app_test"}
    )
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        "notify",
        "garmin_homeassistant",
        {"message": "Hello", "title": "Hi"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert received == [{"message": "Hello", "title": "Hi"}]


async def test_the_notify_platform_ignores_an_empty_discovery(hass: HomeAssistant) -> None:
    """Without a client the platform does not register anything."""
    from custom_components.garmin_homeassistant.notify import async_get_service

    assert await async_get_service(hass, {}, None) is None
    assert await async_get_service(hass, {}, {}) is None


async def test_the_bridge_is_contacted_over_the_configured_url(
    hass: HomeAssistant, mock_bridge, mock_config_entry, bridge_url
) -> None:
    """Every request carries the bearer token of the config entry."""
    await _setup(hass, mock_config_entry)

    await hass.services.async_call(
        "notify",
        "garmin_homeassistant",
        {"message": "Hello"},
        blocking=True,
    )

    for _method, url, _payload, headers in mock_bridge.mock_calls:
        assert str(url).startswith(bridge_url)
        assert headers["Authorization"] == "Bearer bridge-token"

    assert DOMAIN == "garmin_homeassistant"
