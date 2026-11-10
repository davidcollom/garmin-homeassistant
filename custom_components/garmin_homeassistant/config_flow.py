"""Config flow for the Garmin Home Assistant integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import BridgeClient
from .const import (
    CONF_BLOCKED_ENTITIES,
    CONF_BRIDGE_TOKEN,
    CONF_BRIDGE_URL,
    CONF_CREATE_MIRROR_SWITCHES,
    CONF_EXPOSED_ENTITIES,
    CONF_PHONE_NOTIFY_SERVICE,
    CONF_SCAN_INTERVAL,
    DEFAULT_BRIDGE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

#: Domains whose entities make sense to control from a watch.
WATCHABLE_DOMAINS = [
    "light",
    "switch",
    "lock",
    "cover",
    "climate",
    "fan",
    "input_boolean",
    "humidifier",
    "media_player",
    "remote",
    "scene",
    "script",
    "vacuum",
    "alarm_control_panel",
]


def _user_schema(default_url: str = DEFAULT_BRIDGE_URL) -> vol.Schema:
    """Return the schema for the initial setup step."""
    return vol.Schema(
        {
            vol.Required(CONF_BRIDGE_URL, default=default_url): str,
            vol.Required(CONF_BRIDGE_TOKEN): str,
        }
    )


def _options_schema(options: Mapping[str, Any]) -> vol.Schema:
    """Return the schema for the options flow."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_EXPOSED_ENTITIES,
                default=list(options.get(CONF_EXPOSED_ENTITIES) or []),
            ): EntitySelector(
                EntitySelectorConfig(
                    domain=WATCHABLE_DOMAINS,
                    multiple=True,
                )
            ),
            vol.Optional(
                CONF_BLOCKED_ENTITIES,
                default=list(options.get(CONF_BLOCKED_ENTITIES) or []),
            ): EntitySelector(
                EntitySelectorConfig(
                    domain=WATCHABLE_DOMAINS,
                    multiple=True,
                )
            ),
            vol.Optional(
                CONF_PHONE_NOTIFY_SERVICE,
                default=options.get(CONF_PHONE_NOTIFY_SERVICE) or "",
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CREATE_MIRROR_SWITCHES,
                default=bool(options.get(CONF_CREATE_MIRROR_SWITCHES, False)),
            ): BooleanSelector(),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=5,
                    max=3600,
                    step=5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


class GarminConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of the bridge."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Ask for the bridge address and token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = str(user_input[CONF_BRIDGE_URL]).rstrip("/")
            token = str(user_input[CONF_BRIDGE_TOKEN]).strip()

            client = BridgeClient(async_get_clientsession(self.hass), url, token)
            if await client.async_valid():
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Garmin Bridge ({url})",
                    data={CONF_BRIDGE_URL: url, CONF_BRIDGE_TOKEN: token},
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> Any:
        """Handle configuration through yaml."""
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return GarminOptionsFlow()


class GarminOptionsFlow(OptionsFlow):
    """Handle the options for an existing entry."""

    @property
    def _entry(self) -> ConfigEntry:
        """Return the config entry the options belong to."""
        # Home Assistant 2025.1 and newer expose the entry directly.
        entry = getattr(self, "config_entry", None)
        if entry is not None:
            return entry
        found = self.hass.config_entries.async_get_entry(self.handler)
        if found is None:
            raise ValueError(f"Unknown config entry {self.handler}")
        return found

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self._entry.options),
        )
