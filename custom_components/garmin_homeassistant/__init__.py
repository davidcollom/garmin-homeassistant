"""The Garmin Home Assistant integration.

Connects Home Assistant to the Garmin bridge, which in turn is reached by the
Connect IQ watch app running on the watch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.components.notify import ATTR_MESSAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import BridgeClient
from .const import (
    ATTR_WATCH_ID,
    CONF_BLOCKED_ENTITIES,
    CONF_BRIDGE_TOKEN,
    CONF_BRIDGE_URL,
    CONF_EXPOSED_ENTITIES,
    CONF_PHONE_NOTIFY_SERVICE,
    DATA_CLIENT,
    DEFAULT_NOTIFY_TITLE,
    DOMAIN,
    SERVICE_REFRESH,
    SERVICE_RUN_COMMAND,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_SET_EXPOSED_ENTITIES,
)
from .coordinator import GarminCoordinator
from .helpers import split_service_name

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]

SERVICE_SEND_NOTIFICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional("title", default=DEFAULT_NOTIFY_TITLE): cv.string,
        vol.Optional("priority", default="normal"): vol.In(["low", "normal", "high"]),
        vol.Optional("actions"): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("id"): cv.string,
                        vol.Required("label"): cv.string,
                    }
                )
            ],
        ),
        vol.Optional(ATTR_ENTITY_ID): cv.string,
        vol.Optional(ATTR_WATCH_ID): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_RUN_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("command"): cv.string,
        vol.Optional(ATTR_ENTITY_ID): cv.string,
        vol.Optional("data", default={}): dict,
    }
)

SERVICE_SET_EXPOSED_ENTITIES_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_ids", default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


@dataclass(slots=True)
class GarminRuntimeData:
    """Objects shared by the platforms of a config entry."""

    client: BridgeClient
    coordinator: GarminCoordinator


type GarminConfigEntry = ConfigEntry[GarminRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: GarminConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    session = async_get_clientsession(hass)
    client = BridgeClient(
        session,
        entry.data[CONF_BRIDGE_URL],
        entry.data[CONF_BRIDGE_TOKEN],
    )
    coordinator = GarminCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001 - surfaced to the user
        _LOGGER.error("Could not connect to the Garmin bridge: %s", err)
        raise ConfigEntryNotReady(
            f"Could not connect to the Garmin bridge at {entry.data[CONF_BRIDGE_URL]}"
        ) from err

    entry.runtime_data = GarminRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)
    _apply_exposure(hass, entry)

    # The notify platform is loaded through discovery so the service is
    # registered as notify.garmin_homeassistant.
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: "Garmin Homeassistant",
                DATA_CLIENT: client,
                CONF_PHONE_NOTIFY_SERVICE: entry.options.get(CONF_PHONE_NOTIFY_SERVICE, ""),
            },
            {},
        )
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarminConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        _unregister_services(hass)
        try:
            from homeassistant.components.notify import async_reset_platform

            await async_reset_platform(hass, DOMAIN)
        except Exception:  # noqa: BLE001 - the notify component may not be loaded
            pass
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: GarminConfigEntry) -> None:
    """Reload the entry when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _apply_exposure(hass: HomeAssistant, entry: GarminConfigEntry) -> None:
    """Push the configured exposure list to the bridge."""

    async def _apply() -> None:
        try:
            await entry.runtime_data.client.async_set_exposed(
                exposed=list(entry.options.get(CONF_EXPOSED_ENTITIES) or []),
                blocked=list(entry.options.get(CONF_BLOCKED_ENTITIES) or []),
            )
        except Exception as err:  # noqa: BLE001 - best effort
            _LOGGER.warning("Could not update the exposed entities on the bridge: %s", err)

    hass.async_create_task(_apply())


def _register_services(hass: HomeAssistant) -> None:
    """Register the integration services once."""

    async def async_send_notification(call: ServiceCall) -> None:
        """Queue a notification for the watches."""
        entry = _first_entry(hass)
        if entry is None:
            _LOGGER.warning("No Garmin bridge is configured")
            return
        actions = [
            {"id": str(item["id"]), "label": str(item["label"])}
            for item in (call.data.get("actions") or [])
        ]
        await entry.runtime_data.client.async_notify(
            title=str(call.data.get("title") or DEFAULT_NOTIFY_TITLE),
            message=str(call.data[ATTR_MESSAGE]),
            priority=str(call.data.get("priority") or "normal"),
            actions=actions,
            entity_id=call.data.get(ATTR_ENTITY_ID),
            watch_ids=call.data.get(ATTR_WATCH_ID),
        )
        await _mirror_to_phone(hass, call)

    async def async_run_command(call: ServiceCall) -> dict[str, Any]:
        """Run a command through the bridge."""
        entry = _first_entry(hass)
        if entry is None:
            _LOGGER.warning("No Garmin bridge is configured")
            return {"ok": False, "message": "No Garmin bridge is configured"}
        result = await entry.runtime_data.client.async_command(
            command=str(call.data["command"]),
            entity_id=call.data.get(ATTR_ENTITY_ID),
            data=dict(call.data.get("data") or {}),
        )
        return result

    async def async_set_exposed(call: ServiceCall) -> None:
        """Change which entities the watches can see."""
        entry = _first_entry(hass)
        if entry is None:
            _LOGGER.warning("No Garmin bridge is configured")
            return
        entity_ids = list(call.data.get("entity_ids") or [])
        await entry.runtime_data.client.async_set_exposed(exposed=entity_ids)
        options = dict(entry.options)
        options[CONF_EXPOSED_ENTITIES] = entity_ids
        hass.config_entries.async_update_entry(entry, options=options)

    async def async_refresh(call: ServiceCall) -> None:
        """Ask the bridge to re-read the Home Assistant states."""
        entry = _first_entry(hass)
        if entry is None:
            return
        await entry.runtime_data.client.async_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_NOTIFICATION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_NOTIFICATION,
            async_send_notification,
            schema=SERVICE_SEND_NOTIFICATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RUN_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RUN_COMMAND,
            async_run_command,
            schema=SERVICE_RUN_COMMAND_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_EXPOSED_ENTITIES):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_EXPOSED_ENTITIES,
            async_set_exposed,
            schema=SERVICE_SET_EXPOSED_ENTITIES_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            async_refresh,
        )


def _unregister_services(hass: HomeAssistant) -> None:
    """Remove the integration services."""
    for service in (
        SERVICE_SEND_NOTIFICATION,
        SERVICE_RUN_COMMAND,
        SERVICE_SET_EXPOSED_ENTITIES,
        SERVICE_REFRESH,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


def _first_entry(hass: HomeAssistant) -> GarminConfigEntry | None:
    """Return the first configured bridge entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def _mirror_to_phone(hass: HomeAssistant, call: ServiceCall) -> None:
    """Optionally mirror a notification to the paired phone.

    The Garmin Connect mobile app mirrors phone notifications to the watch, so
    this gives near instant delivery even when the watch app is not running.
    """
    entry = _first_entry(hass)
    if entry is None:
        return
    service = entry.options.get(CONF_PHONE_NOTIFY_SERVICE) or ""
    if not service:
        return
    domain, name = split_service_name(service)
    try:
        await hass.services.async_call(
            domain,
            name,
            {
                ATTR_MESSAGE: str(call.data[ATTR_MESSAGE]),
                "title": str(call.data.get("title") or DEFAULT_NOTIFY_TITLE),
            },
            blocking=False,
        )
    except Exception as err:  # noqa: BLE001 - best effort delivery
        _LOGGER.warning("Could not mirror the notification to %s: %s", service, err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from yaml (not supported)."""
    return True
