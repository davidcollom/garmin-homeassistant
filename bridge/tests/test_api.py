"""Tests for the HTTP surface of the bridge."""

from __future__ import annotations

import json

from conftest import FakeHomeAssistant
from fastapi.testclient import TestClient

from garmin_bridge.app import create_app
from garmin_bridge.config import BridgeConfig


def test_health_is_unauthenticated(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_endpoints_require_a_token(client: TestClient) -> None:
    assert client.get("/v1/entities").status_code == 401
    assert client.get("/v1/entities", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_admin_requires_the_bridge_token(client: TestClient, watch_headers: dict[str, str]) -> None:
    assert client.get("/v1/admin/entities", headers=watch_headers).status_code == 401
    assert (
        client.get(
            "/v1/admin/entities", headers={"Authorization": "Bearer bridge-token"}
        ).status_code
        == 200
    )


def test_entities_are_serialised_as_compact_arrays(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    fake_ha.set_state("light.kitchen", "on", {"friendly_name": "Kitchen"}, area="Kitchen")

    response = client.get("/v1/entities", headers=watch_headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["e"] == [["light.kitchen", "Kitchen", "light", "on", 1, 0, None]]
    assert payload["areas"] == ["Kitchen"]
    assert payload["n"] == 1
    assert payload["more"] is False


def test_entities_can_be_paged(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    for index in range(7):
        fake_ha.set_state(f"light.l{index}", "on")

    first = client.get("/v1/entities?limit=3&offset=0", headers=watch_headers).json()
    assert len(first["e"]) == 3
    assert first["n"] == 7
    assert first["more"] is True

    last = client.get("/v1/entities?limit=3&offset=6", headers=watch_headers).json()
    assert len(last["e"]) == 1
    assert last["more"] is False


def test_delta_requests_only_return_changes(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    fake_ha.set_state("light.a", "on")
    fake_ha.set_state("light.b", "on")
    revision = client.get("/v1/entities", headers=watch_headers).json()["rev"]

    fake_ha.set_state("light.b", "off")
    fake_ha.remove_state("light.a")

    payload = client.get(f"/v1/entities?since={revision}", headers=watch_headers).json()
    rows = {row[0]: row for row in payload["e"]}
    assert "light.b" in rows
    assert rows["light.b"][3] == "off"
    assert payload["r"] == ["light.a"]


def test_register_returns_a_watch_token(client: TestClient, watch_headers: dict[str, str]) -> None:
    payload = {
        "watch_id": "watch-1",
        "name": "Garmin",
        "model": "282x470",
        "api_level": 600,
        "capabilities": {"touch": True},
    }

    response = client.post("/v1/watches/register", json=payload, headers=watch_headers)
    assert response.status_code == 200

    body = response.json()
    assert body["watch_id"] == "watch-1"
    token = body["token"]
    assert token

    # The issued token authenticates the watch on its own.
    own = {"Authorization": f"Bearer {token}", "X-Garmin-Watch-Id": "watch-1"}
    assert client.get("/v1/entities", headers=own).status_code == 200
    assert client.get("/v1/entities", headers=watch_headers).status_code == 200


def test_commands_reach_home_assistant(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    fake_ha.set_state("light.kitchen", "off")

    response = client.post(
        "/v1/commands",
        json={"cmd": "toggle", "entity_id": "light.kitchen"},
        headers=watch_headers,
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake_ha.calls
    domain, service, entity_id, _data = fake_ha.calls[-1]
    assert domain == "light"
    assert service == "turn_on"
    assert entity_id == "light.kitchen"


def test_commands_accept_a_form_encoded_body(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    """Connect IQ runtimes before 6.0.3 cannot send a JSON body."""
    response = client.post(
        "/v1/commands",
        data={"json": json.dumps({"cmd": "turn_on", "entity_id": "light.kitchen"})},
        headers={**watch_headers, "Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert fake_ha.calls[-1][1] == "turn_on"


def test_commands_accept_plain_form_fields(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/commands",
        data={"cmd": "turn_off", "entity_id": "light.kitchen"},
        headers={**watch_headers, "Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert fake_ha.calls[-1][1] == "turn_off"


def test_notifications_are_queued_and_acknowledged(
    client: TestClient,
    fake_ha: FakeHomeAssistant,
    admin_headers: dict[str, str],
    watch_headers: dict[str, str],
) -> None:
    client.post(
        "/v1/watches/register",
        json={"watch_id": "watch-1", "name": "Garmin"},
        headers=watch_headers,
    )

    queued = client.post(
        "/v1/admin/notify",
        json={
            "title": "Doorbell",
            "body": "Someone is at the door",
            "actions": [{"id": "open", "label": "Open"}],
            "entity_id": "binary_sensor.front_door",
            "watch_ids": ["watch-1"],
        },
        headers=admin_headers,
    )
    assert queued.status_code == 200
    assert queued.json()["queued"] == 1

    listing = client.get("/v1/notifications", headers=watch_headers).json()
    assert len(listing["n"]) == 1
    row = listing["n"][0]
    assert row[0].startswith("n")
    assert row[2] == "Doorbell"
    assert row[5] == [["open", "Open"]]

    notification_id = row[0]
    acked = client.post(
        f"/v1/notifications/{notification_id}/ack",
        json={"action": "open"},
        headers=watch_headers,
    )
    assert acked.status_code == 200

    assert client.get("/v1/notifications", headers=watch_headers).json()["n"] == []

    # Picking an action fires an event in Home Assistant.
    assert fake_ha.events
    event_type, payload = fake_ha.events[-1]
    assert event_type == "garmin_homeassistant_watch_action"
    assert payload["action"] == "open"
    assert payload["watch_id"] == "watch-1"
    assert payload["entity_id"] == "binary_sensor.front_door"


def test_watch_events_are_forwarded_to_home_assistant(
    client: TestClient, fake_ha: FakeHomeAssistant, watch_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/events",
        json={"type": "button", "button": "start", "message": "hello"},
        headers=watch_headers,
    )

    assert response.status_code == 200
    assert fake_ha.events
    event_type, data = fake_ha.events[-1]
    assert event_type == "garmin_watch_button"
    assert data["button"] == "start"


def test_config_endpoint_reports_the_poll_interval(
    client: TestClient, watch_headers: dict[str, str]
) -> None:
    payload = client.get("/v1/config", headers=watch_headers).json()
    assert payload["poll_interval"] >= 10
    assert payload["background_interval"] >= 300
    assert payload["page_size"] > 0


def test_admin_config_updates_the_exposure(
    client: TestClient, fake_ha: FakeHomeAssistant, admin_headers: dict[str, str]
) -> None:
    fake_ha.set_state("light.a", "on")
    fake_ha.set_state("light.b", "on")

    response = client.post(
        "/v1/admin/config",
        json={"blocked_entities": ["light.b"]},
        headers=admin_headers,
    )
    assert response.status_code == 200

    entities = client.get("/v1/admin/entities", headers=admin_headers).json()
    assert [item["entity_id"] for item in entities["entities"]] == ["light.a"]


def test_the_base_allow_list_limits_the_integration(
    config: BridgeConfig, fake_ha: FakeHomeAssistant, admin_headers: dict[str, str]
) -> None:
    """The allow list of the bridge survives the configuration of the integration."""
    config.entity_allowlist = ("light.a",)
    app = create_app(config)
    app.state.bridge.ha = fake_ha

    with TestClient(app) as client:
        fake_ha.set_state("light.a", "on")
        fake_ha.set_state("light.b", "on")

        # The integration pushes an empty list, which means "everything the
        # base list allows" and not "nothing".
        client.post(
            "/v1/admin/config",
            json={"exposed_entities": [], "blocked_entities": []},
            headers=admin_headers,
        )

        entities = client.get("/v1/admin/entities", headers=admin_headers).json()
        assert [item["entity_id"] for item in entities["entities"]] == ["light.a"]


def test_the_integration_narrows_the_base_allow_list(
    config: BridgeConfig, fake_ha: FakeHomeAssistant, admin_headers: dict[str, str]
) -> None:
    """The selection of the integration is applied inside the base list."""
    config.entity_allowlist = ("light.a", "light.b")
    app = create_app(config)
    app.state.bridge.ha = fake_ha

    with TestClient(app) as client:
        fake_ha.set_state("light.a", "on")
        fake_ha.set_state("light.b", "on")
        fake_ha.set_state("light.c", "on")

        client.post(
            "/v1/admin/config",
            json={"exposed_entities": ["light.b", "light.c"]},
            headers=admin_headers,
        )

        entities = client.get("/v1/admin/entities", headers=admin_headers).json()
        assert [item["entity_id"] for item in entities["entities"]] == ["light.b"]


def test_the_base_block_list_is_not_overwritten(
    config: BridgeConfig, fake_ha: FakeHomeAssistant, admin_headers: dict[str, str]
) -> None:
    """An entity the bridge blocks stays blocked."""
    config.entity_blocklist = ("light.b",)
    app = create_app(config)
    app.state.bridge.ha = fake_ha

    with TestClient(app) as client:
        fake_ha.set_state("light.a", "on")
        fake_ha.set_state("light.b", "on")

        client.post(
            "/v1/admin/config",
            json={"exposed_entities": [], "blocked_entities": []},
            headers=admin_headers,
        )

        entities = client.get("/v1/admin/entities", headers=admin_headers).json()
        assert [item["entity_id"] for item in entities["entities"]] == ["light.a"]


def test_admin_can_forget_a_watch(
    client: TestClient, admin_headers: dict[str, str], watch_headers: dict[str, str]
) -> None:
    client.post(
        "/v1/watches/register",
        json={"watch_id": "watch-1", "name": "Garmin"},
        headers=watch_headers,
    )
    assert client.get("/v1/admin/watches", headers=admin_headers).json()["watches"]

    deleted = client.delete("/v1/admin/watches/watch-1", headers=admin_headers)
    assert deleted.json()["removed"] is True
    assert client.get("/v1/admin/watches", headers=admin_headers).json()["watches"] == []


def test_pinned_watch_tokens_are_accepted(config: BridgeConfig, fake_ha: FakeHomeAssistant) -> None:
    config.watch_tokens = {"watch-9": "pinned-token"}
    app = create_app(config)
    app.state.bridge.ha = fake_ha

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer pinned-token", "X-Garmin-Watch-Id": "watch-9"}
        assert client.get("/v1/entities", headers=headers).status_code == 200
