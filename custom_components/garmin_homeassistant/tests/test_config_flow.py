"""Tests for the config and options flow of the Garmin integration."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.garmin_homeassistant.const import (
    CONF_BRIDGE_TOKEN,
    CONF_BRIDGE_URL,
    CONF_CREATE_MIRROR_SWITCHES,
    CONF_EXPOSED_ENTITIES,
    CONF_PHONE_NOTIFY_SERVICE,
    DOMAIN,
)


async def test_the_user_flow_creates_an_entry(
    hass: HomeAssistant, aioclient_mock, bridge_url, bridge_token
) -> None:
    """A reachable bridge is accepted."""
    aioclient_mock.get(
        f"{bridge_url}/v1/health",
        json={"ok": True},
        headers={"content-type": "application/json"},
    )

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BRIDGE_URL: bridge_url, CONF_BRIDGE_TOKEN: bridge_token},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_BRIDGE_URL: bridge_url,
        CONF_BRIDGE_TOKEN: bridge_token,
    }
    assert result["title"] == f"Garmin Bridge ({bridge_url})"


async def test_the_user_flow_reports_a_wrong_token(
    hass: HomeAssistant, aioclient_mock, bridge_url
) -> None:
    """A bridge that rejects the token shows an error."""
    aioclient_mock.get(
        f"{bridge_url}/v1/health",
        status=401,
        json={"detail": "nope"},
        headers={"content-type": "application/json"},
    )

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BRIDGE_URL: bridge_url, CONF_BRIDGE_TOKEN: "wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_the_user_flow_aborts_for_a_known_bridge(
    hass: HomeAssistant, aioclient_mock, mock_config_entry, bridge_url, bridge_token
) -> None:
    """The same bridge is not added twice."""
    aioclient_mock.get(
        f"{bridge_url}/v1/health",
        json={"ok": True},
        headers={"content-type": "application/json"},
    )
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        unique_id=bridge_url,
    )

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BRIDGE_URL: bridge_url, CONF_BRIDGE_TOKEN: bridge_token},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_the_options_flow_stores_the_settings(
    hass: HomeAssistant, mock_bridge, mock_config_entry
) -> None:
    """The options are stored on the config entry."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_EXPOSED_ENTITIES: ["light.kitchen"],
            CONF_PHONE_NOTIFY_SERVICE: "mobile_app_test",
            CONF_CREATE_MIRROR_SWITCHES: True,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert mock_config_entry.options[CONF_EXPOSED_ENTITIES] == ["light.kitchen"]
    assert mock_config_entry.options[CONF_PHONE_NOTIFY_SERVICE] == "mobile_app_test"
    assert mock_config_entry.options[CONF_CREATE_MIRROR_SWITCHES] is True
