"""Tests for the command translation layer."""

from __future__ import annotations

from typing import Any

import pytest

from garmin_bridge.commands import CommandExecutor
from garmin_bridge.ha import HomeAssistantError
from garmin_bridge.models import CommandRequest


class FakeHA:
    """A Home Assistant stand-in for the command executor."""

    def __init__(self) -> None:
        self.states: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str, str | None, dict[str, Any]]] = []
        self.error: Exception | None = None

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        if self.error is not None:
            raise self.error
        self.calls.append((domain, service, entity_id, dict(data or {})))
        return []


@pytest.fixture
def ha() -> FakeHA:
    return FakeHA()


@pytest.fixture
def executor(ha: FakeHA) -> CommandExecutor:
    return CommandExecutor(ha)  # type: ignore[arg-type]


def _set(ha: FakeHA, entity_id: str, state: str) -> None:
    ha.states[entity_id] = {"entity_id": entity_id, "state": state, "attributes": {}}


async def test_toggle_turns_an_off_light_on(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "light.kitchen", "off")

    result = await executor.execute(CommandRequest(cmd="toggle", entity_id="light.kitchen"))

    assert result.ok is True
    assert ha.calls[-1][1] == "turn_on"


async def test_toggle_turns_an_on_light_off(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "light.kitchen", "on")

    await executor.execute(CommandRequest(cmd="toggle", entity_id="light.kitchen"))

    assert ha.calls[-1][1] == "turn_off"


async def test_toggle_unlocks_a_locked_lock(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "lock.front", "locked")

    await executor.execute(CommandRequest(cmd="toggle", entity_id="lock.front"))

    assert ha.calls[-1][1] == "unlock"


async def test_toggle_locks_an_unlocked_lock(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "lock.front", "unlocked")

    await executor.execute(CommandRequest(cmd="toggle", entity_id="lock.front"))

    assert ha.calls[-1][1] == "lock"


async def test_toggle_disarms_an_armed_alarm(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "alarm_control_panel.home", "armed_away")

    await executor.execute(CommandRequest(cmd="toggle", entity_id="alarm_control_panel.home"))

    assert ha.calls[-1][1] == "alarm_disarm"


async def test_toggle_opens_a_closed_cover(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "cover.garage", "closed")

    await executor.execute(CommandRequest(cmd="toggle", entity_id="cover.garage"))

    assert ha.calls[-1][1] == "open_cover"


async def test_set_level_uses_the_domain_specific_payload(
    executor: CommandExecutor, ha: FakeHA
) -> None:
    _set(ha, "light.kitchen", "on")

    await executor.execute(
        CommandRequest(
            cmd="set_level",
            entity_id="light.kitchen",
            data={"value": 40},
        )
    )

    domain, service, _, data = ha.calls[-1]
    assert (domain, service) == ("light", "turn_on")
    assert data == {"brightness_pct": 40}


async def test_set_level_on_a_climate_uses_a_temperature(
    executor: CommandExecutor, ha: FakeHA
) -> None:
    _set(ha, "climate.lounge", "heat")

    await executor.execute(
        CommandRequest(
            cmd="set_level",
            entity_id="climate.lounge",
            data={"value": 21.5},
        )
    )

    domain, service, _, data = ha.calls[-1]
    assert (domain, service) == ("climate", "set_temperature")
    assert data == {"temperature": 21.5}


async def test_set_level_without_a_value_fails(executor: CommandExecutor) -> None:
    result = await executor.execute(CommandRequest(cmd="set_level", entity_id="light.kitchen"))

    assert result.ok is False
    assert "value" in result.message.lower()


async def test_explicit_service_accepts_a_qualified_name(
    executor: CommandExecutor, ha: FakeHA
) -> None:
    result = await executor.execute(
        CommandRequest(cmd="service", service="light.turn_on", entity_id="light.kitchen")
    )

    assert result.ok is True
    assert ha.calls[-1][:2] == ("light", "turn_on")


async def test_explicit_service_without_a_name_fails(executor: CommandExecutor) -> None:
    result = await executor.execute(CommandRequest(cmd="service"))

    assert result.ok is False


async def test_a_command_without_an_entity_fails(executor: CommandExecutor) -> None:
    result = await executor.execute(CommandRequest(cmd="toggle"))

    assert result.ok is False
    assert result.message == "No entity specified"


async def test_an_unknown_command_fails(executor: CommandExecutor) -> None:
    result = await executor.execute(CommandRequest(cmd="explode", entity_id="light.kitchen"))

    assert result.ok is False
    assert "explode" in result.message


async def test_home_assistant_errors_are_reported(executor: CommandExecutor, ha: FakeHA) -> None:
    ha.error = HomeAssistantError("boom")

    result = await executor.execute(CommandRequest(cmd="toggle", entity_id="light.kitchen"))

    assert result.ok is False
    assert "boom" in result.message


async def test_extra_services_are_reachable(executor: CommandExecutor, ha: FakeHA) -> None:
    _set(ha, "media_player.tv", "playing")

    await executor.execute(CommandRequest(cmd="next", entity_id="media_player.tv"))

    assert ha.calls[-1][1] == "media_next_track"
