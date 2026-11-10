"""Fixtures for the Garmin Home Assistant integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The repository root has to be importable so that ``import custom_components``
# finds the integration.  That is how Home Assistant discovers custom
# integrations, see ``homeassistant.loader._get_custom_components``.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

pytest_plugins = "pytest_homeassistant_custom_component"

from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.garmin_homeassistant.const import (  # noqa: E402
    CONF_BRIDGE_TOKEN,
    CONF_BRIDGE_URL,
    DOMAIN,
)

BRIDGE_URL = "http://bridge:8099"
BRIDGE_TOKEN = "bridge-token"

#: The mock needs an explicit content type, otherwise the response is text.
JSON_HEADERS = {"content-type": "application/json"}

WATCHES = [
    {
        "watch_id": "edge1040-1",
        "name": "Edge 1040",
        "model": "282x470",
        "api_level": 600,
        "last_seen": 1_700_000_000,
        "battery": 72,
        "steps": 4321,
        "heart_rate": 61,
    }
]

ENTITIES = [
    {
        "entity_id": "light.kitchen",
        "name": "Kitchen",
        "domain": "light",
        "state": "on",
        "area": "Downstairs",
        "flags": 1,
        "value": None,
    },
    {
        "entity_id": "lock.front_door",
        "name": "Front door",
        "domain": "lock",
        "state": "locked",
        "area": None,
        "flags": 8,
        "value": None,
    },
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration in every test."""
    yield


@pytest.fixture
def bridge_url() -> str:
    """The URL of the fake bridge."""
    return BRIDGE_URL


@pytest.fixture
def bridge_token() -> str:
    """The token of the fake bridge."""
    return BRIDGE_TOKEN


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A config entry that points at the fake bridge."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_BRIDGE_URL: BRIDGE_URL, CONF_BRIDGE_TOKEN: BRIDGE_TOKEN},
        options={},
    )


@pytest.fixture
def mock_bridge(aioclient_mock):
    """Mock the endpoints of the bridge that the integration uses."""
    aioclient_mock.get(
        f"{BRIDGE_URL}/v1/admin/watches",
        json={"watches": WATCHES},
        headers=JSON_HEADERS,
    )
    aioclient_mock.get(
        f"{BRIDGE_URL}/v1/admin/entities",
        json={"entities": ENTITIES},
        headers=JSON_HEADERS,
    )
    aioclient_mock.get(
        f"{BRIDGE_URL}/v1/health",
        json={"ok": True},
        headers=JSON_HEADERS,
    )
    aioclient_mock.post(
        f"{BRIDGE_URL}/v1/admin/config",
        json={"exposed_entities": [], "blocked_entities": []},
        headers=JSON_HEADERS,
    )
    aioclient_mock.post(
        f"{BRIDGE_URL}/v1/admin/refresh",
        json={"ok": True, "rev": 1},
        headers=JSON_HEADERS,
    )
    aioclient_mock.post(
        f"{BRIDGE_URL}/v1/admin/notify",
        json={"queued": 1, "ids": ["n1"]},
        headers=JSON_HEADERS,
    )
    aioclient_mock.post(
        f"{BRIDGE_URL}/v1/commands",
        json={"ok": True, "message": "light.turn_on"},
        headers=JSON_HEADERS,
    )
    return aioclient_mock
