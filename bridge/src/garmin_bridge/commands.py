"""Translate compact watch commands into Home Assistant service calls."""

from __future__ import annotations

import logging
from typing import Any

from .ha import HomeAssistantClient, HomeAssistantError
from .models import CommandRequest, CommandResponse

_LOGGER = logging.getLogger(__name__)

#: States that mean "currently active" when toggling.
_ACTIVE_STATES = {
    "on",
    "open",
    "open_cover",
    "playing",
    "home",
    "armed_away",
    "armed_home",
    "armed_night",
    "armed_vacation",
    "armed_custom_bypass",
    "locked",
    "active",
    "heat",
    "cool",
    "auto",
}

#: Per-domain service names used for the generic on/off commands.
_ON_SERVICES = {
    "alarm_control_panel": "alarm_arm_away",
    "climate": "turn_on",
    "cover": "open_cover",
    "fan": "turn_on",
    "humidifier": "turn_on",
    "input_boolean": "turn_on",
    "light": "turn_on",
    "lock": "unlock",
    "media_player": "media_play",
    "remote": "turn_on",
    "scene": "turn_on",
    "script": "turn_on",
    "switch": "turn_on",
    "vacuum": "start",
}

_OFF_SERVICES = {
    "alarm_control_panel": "alarm_disarm",
    "climate": "turn_off",
    "cover": "close_cover",
    "fan": "turn_off",
    "humidifier": "turn_off",
    "input_boolean": "turn_off",
    "light": "turn_off",
    "lock": "lock",
    "media_player": "media_pause",
    "remote": "turn_off",
    "switch": "turn_off",
    "vacuum": "return_to_base",
}

#: Extra services offered per domain, surfaced as watch actions.
EXTRA_SERVICES: dict[str, dict[str, str]] = {
    "alarm_control_panel": {
        "arm_home": "alarm_arm_home",
        "arm_away": "alarm_arm_away",
        "disarm": "alarm_disarm",
    },
    "climate": {
        "heat": "set_temperature",
        "cool": "set_temperature",
        "off": "turn_off",
    },
    "cover": {
        "stop": "stop_cover",
    },
    "lock": {
        "unlock": "unlock",
        "lock": "lock",
    },
    "media_player": {
        "play": "media_play",
        "pause": "media_pause",
        "next": "media_next_track",
        "previous": "media_previous_track",
    },
    "vacuum": {
        "start": "start",
        "pause": "pause",
        "dock": "return_to_base",
    },
}


class CommandExecutor:
    """Executes watch commands against Home Assistant."""

    def __init__(self, ha: HomeAssistantClient) -> None:
        self._ha = ha

    async def execute(self, command: CommandRequest) -> CommandResponse:
        """Run a command and return a watch friendly result."""
        if not command.entity_id and command.cmd != "service":
            return CommandResponse(ok=False, message="No entity specified")

        domain = command.domain
        if command.entity_id and not domain:
            domain = command.entity_id.split(".", 1)[0]

        if command.cmd == "service":
            return await self._explicit_service(command, domain)
        if command.entity_id is None:
            return CommandResponse(ok=False, message="No entity specified")

        state = self._current_state(command.entity_id)

        try:
            if command.cmd == "toggle":
                return await self._toggle(command.entity_id, domain, state)
            if command.cmd in {"turn_on", "on"}:
                service = _ON_SERVICES.get(domain or "", "turn_on")
                return await self._call(command.entity_id, service, command.data)
            if command.cmd in {"turn_off", "off"}:
                service = _OFF_SERVICES.get(domain or "", "turn_off")
                return await self._call(command.entity_id, service, command.data)
            if command.cmd == "open":
                service = _ON_SERVICES.get(domain or "", "open_cover")
                return await self._call(command.entity_id, service, command.data)
            if command.cmd == "close":
                service = _OFF_SERVICES.get(domain or "", "close_cover")
                return await self._call(command.entity_id, service, command.data)
            if command.cmd in {"set_level", "set_value"}:
                return await self._set_level(command, domain)
            if command.cmd in EXTRA_SERVICES.get(domain or "", {}):
                service = EXTRA_SERVICES[domain or ""][command.cmd]
                return await self._call(command.entity_id, service, command.data)
        except HomeAssistantError as exc:
            _LOGGER.warning("Command %s failed: %s", command.cmd, exc)
            return CommandResponse(ok=False, message=str(exc)[:120])

        return CommandResponse(ok=False, message=f"Unsupported command: {command.cmd}")

    # -- helpers -----------------------------------------------------------

    def _current_state(self, entity_id: str) -> str:
        entity = self._ha.states.get(entity_id)
        if not entity:
            return "unknown"
        return str(entity.get("state", "unknown")).lower()

    async def _call(
        self,
        entity_id: str,
        service: str,
        data: dict[str, Any],
    ) -> CommandResponse:
        domain = entity_id.split(".", 1)[0]
        await self._ha.call_service(domain, service, entity_id, data)
        return CommandResponse(
            ok=True,
            message=f"{domain}.{service}",
            state=self._current_state(entity_id),
        )

    async def _toggle(
        self,
        entity_id: str,
        domain: str | None,
        state: str,
    ) -> CommandResponse:
        if domain == "alarm_control_panel" and state.startswith("armed"):
            return await self._call(entity_id, "alarm_disarm", {})
        if domain == "lock":
            service = "unlock" if state == "locked" else "lock"
            return await self._call(entity_id, service, {})
        if domain == "cover":
            service = "open_cover" if state in {"closed", "closing"} else "close_cover"
            return await self._call(entity_id, service, {})
        if domain == "vacuum":
            service = "pause" if state == "cleaning" else "start"
            return await self._call(entity_id, service, {})
        if domain == "media_player":
            service = "media_pause" if state == "playing" else "media_play"
            return await self._call(entity_id, service, {})

        service = (
            _OFF_SERVICES.get(domain or "", "turn_off")
            if state in _ACTIVE_STATES
            else _ON_SERVICES.get(domain or "", "turn_on")
        )
        return await self._call(entity_id, service, {})

    async def _set_level(self, command: CommandRequest, domain: str | None) -> CommandResponse:
        entity_id = command.entity_id or ""
        value = command.data.get("value")
        if value is None:
            return CommandResponse(ok=False, message="Missing value")
        payload: dict[str, Any] = {}
        if domain == "climate":
            payload["temperature"] = value
            service = "set_temperature"
        elif domain == "light":
            payload["brightness_pct"] = value
            service = "turn_on"
        elif domain == "cover":
            payload["position"] = value
            service = "set_cover_position"
        else:
            payload["percentage"] = value
            service = "turn_on"
        return await self._call(entity_id, service, payload)

    async def _explicit_service(
        self,
        command: CommandRequest,
        domain: str | None,
    ) -> CommandResponse:
        service = command.service
        if not service:
            return CommandResponse(ok=False, message="No service specified")
        if "." in service:
            service_domain, service = service.split(".", 1)
        else:
            service_domain = domain or "homeassistant"
        try:
            await self._ha.call_service(service_domain, service, command.entity_id, command.data)
        except HomeAssistantError as exc:
            return CommandResponse(ok=False, message=str(exc)[:120])
        return CommandResponse(
            ok=True,
            message=f"{service_domain}.{service}",
            state=self._current_state(command.entity_id) if command.entity_id else None,
        )
