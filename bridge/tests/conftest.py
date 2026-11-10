"""Shared fixtures for the bridge test suite."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from garmin_bridge.app import create_app
from garmin_bridge.config import BridgeConfig


class FakeHomeAssistant:
    """A Home Assistant stand-in that records the calls the bridge makes."""

    def __init__(self) -> None:
        self.states: dict[str, dict[str, Any]] = {}
        self.areas: dict[str, str] = {}
        self.connected = True
        #: (domain, service, entity_id, data) tuples.
        self.calls: list[tuple[str, str, str | None, dict[str, Any]]] = []
        #: (event type, payload) tuples.
        self.events: list[tuple[str, dict[str, Any]]] = []
        self._listener: Any = None

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def add_listener(self, callback: Any) -> None:
        self._listener = callback

    async def refresh(self) -> None:
        return None

    # -- behaviour ---------------------------------------------------------

    def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
        area: str | None = None,
    ) -> None:
        """Add or update an entity and notify the bridge."""
        self.states[entity_id] = {
            "entity_id": entity_id,
            "state": state,
            "attributes": attributes or {},
        }
        if area is not None:
            self.areas[entity_id] = area
        self.notify()

    def remove_state(self, entity_id: str) -> None:
        """Remove an entity and notify the bridge."""
        self.states.pop(entity_id, None)
        self.areas.pop(entity_id, None)
        self.notify()

    def notify(self) -> None:
        """Trigger the state listener the bridge registered."""
        if self._listener is not None:
            self._listener()

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append((domain, service, entity_id, dict(data or {})))
        return []

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if path.startswith("/api/events/"):
            payload = kwargs.get("json") or {}
            self.events.append((path.rsplit("/", 1)[-1], payload.get("data") or {}))
            return {"message": "ok"}
        return []


@pytest.fixture
def config() -> BridgeConfig:
    """A configuration with all the tokens set."""
    return BridgeConfig(
        home_assistant_url="http://homeassistant:8123",
        home_assistant_token="ha-token",
        bridge_token="bridge-token",
        watch_token="watch-token",
    )


@pytest.fixture
def fake_ha() -> FakeHomeAssistant:
    """The Home Assistant stand-in."""
    return FakeHomeAssistant()


@pytest.fixture
def client(config: BridgeConfig, fake_ha: FakeHomeAssistant) -> Iterator[TestClient]:
    """A test client wired to the fake Home Assistant."""
    app = create_app(config)
    app.state.bridge.ha = fake_ha
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def watch_headers() -> dict[str, str]:
    """Headers a watch sends with every request."""
    return {
        "Authorization": "Bearer watch-token",
        "X-Garmin-Watch-Id": "watch-1",
    }


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Headers the Home Assistant integration sends."""
    return {"Authorization": "Bearer bridge-token"}
