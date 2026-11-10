"""Home Assistant client.

Keeps a live mirror of the Home Assistant entity states and proxies service
calls.  A websocket subscription is used so the bridge reacts to state changes
immediately; a slow poll runs alongside it as a reconciliation safety net in
case the websocket drops.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import aiohttp

from .models import EntityFlags

_LOGGER = logging.getLogger(__name__)

#: Domains whose entities are useful to drive from a watch.
CONTROLLABLE_DOMAINS = frozenset(
    {
        "alarm_control_panel",
        "binary_sensor",
        "climate",
        "cover",
        "fan",
        "humidifier",
        "input_boolean",
        "light",
        "lock",
        "media_player",
        "remote",
        "scene",
        "script",
        "switch",
        "vacuum",
    }
)

#: Domains that are read-only from a watch point of view.
SENSOR_DOMAINS = frozenset({"sensor", "binary_sensor"})

#: Attributes that hold the meaningful numeric value for a domain.
_LEVEL_ATTRIBUTES = (
    "brightness",
    "percentage",
    "current_temperature",
    "temperature",
    "humidity",
    "position",
)


class HomeAssistantError(RuntimeError):
    """Raised when Home Assistant rejects or fails a request."""


class HomeAssistantClient:
    """Talks to the Home Assistant REST and websocket APIs."""

    def __init__(self, url: str, token: str, poll_interval: int = 30) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._poll_interval = poll_interval
        self._session: aiohttp.ClientSession | None = None
        self._states: dict[str, dict[str, Any]] = {}
        self._areas: dict[str, str] = {}
        self._ws_task: asyncio.Task[None] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._connected = False
        self._listeners: list[Any] = []
        self._lock = asyncio.Lock()

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Open the HTTP session and start the sync tasks."""
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        self._ws_task = asyncio.create_task(self._websocket_loop(), name="ha-websocket")
        self._poll_task = asyncio.create_task(self._poll_loop(), name="ha-poll")

    async def stop(self) -> None:
        """Stop the sync tasks and close the HTTP session."""
        for task in (self._ws_task, self._poll_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._ws_task = None
        self._poll_task = None
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._connected = False

    @property
    def connected(self) -> bool:
        """True when the websocket subscription is live."""
        return self._connected

    @property
    def states(self) -> dict[str, dict[str, Any]]:
        """The mirrored Home Assistant states, keyed by entity id."""
        return self._states

    @property
    def areas(self) -> dict[str, str]:
        """Entity id to area name mapping."""
        return self._areas

    # -- subscriptions -----------------------------------------------------

    def add_listener(self, callback: Any) -> None:
        """Register a callback invoked whenever the mirrored state changes."""
        self._listeners.append(callback)

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                result = listener()
            except Exception:  # pragma: no cover - listener bugs must not kill the loop
                _LOGGER.exception("Home Assistant state listener failed")
            else:
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)

    # -- REST --------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._session is None:
            raise HomeAssistantError("Home Assistant client is not started")
        url = f"{self._url}{path}"
        async with self._session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                body = await response.text()
                raise HomeAssistantError(f"Home Assistant returned {response.status}: {body[:200]}")
            if response.content_type == "application/json":
                return await response.json()
            return await response.text()

    async def fetch_states(self) -> list[dict[str, Any]]:
        """Fetch the full entity state list."""
        states = await self._request("GET", "/api/states")
        if not isinstance(states, list):
            raise HomeAssistantError("Unexpected payload from /api/states")
        return states

    async def fetch_area_registry(self) -> dict[str, str]:
        """Fetch entity id to area name mapping, if the API is available."""
        try:
            payload = await self._request(
                "GET",
                "/api/config/area_registry/list",
                params={"type": "entity"},
            )
        except HomeAssistantError:
            # The area registry endpoint is not exposed on every install; the
            # names simply fall back to "unassigned".
            return {}
        areas: dict[str, str] = {}
        for area in payload or []:
            area_id = area.get("area_id")
            name = area.get("name")
            if not area_id or not name:
                continue
            for entity_id in area.get("entity_ids") or []:
                areas[entity_id] = name
        return areas

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke a Home Assistant service."""
        payload: dict[str, Any] = dict(data or {})
        if entity_id:
            payload["entity_id"] = entity_id
        path = f"/api/services/{domain}/{service}"
        return await self._request("POST", path, json=payload)

    # -- background tasks --------------------------------------------------

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self.refresh()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - network dependent
                _LOGGER.warning("Home Assistant poll failed: %s", exc)
            await asyncio.sleep(self._poll_interval)

    async def refresh(self) -> None:
        """Pull the full state list and replace the local mirror."""
        states = await self.fetch_states()
        areas = await self.fetch_area_registry()
        async with self._lock:
            self._states = {item["entity_id"]: item for item in states if item.get("entity_id")}
            self._areas = areas
        self._notify_listeners()

    async def _websocket_loop(self) -> None:
        backoff = 1.0
        while True:
            try:
                await self._websocket_session()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - network dependent
                _LOGGER.warning("Home Assistant websocket error: %s", exc)
                self._connected = False
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    async def _websocket_session(self) -> None:
        if self._session is None:
            raise HomeAssistantError("Home Assistant client is not started")
        ws_url = self._url.replace("https://", "wss://").replace("http://", "ws://")
        async with self._session.ws_connect(f"{ws_url}/api/websocket", heartbeat=30) as ws:
            await ws.send_json({"type": "auth", "access_token": self._token})
            auth_ok = await ws.receive_json()
            if auth_ok.get("type") != "auth_ok":
                raise HomeAssistantError("Home Assistant rejected the websocket auth")
            self._connected = True
            await ws.send_json(
                {
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed",
                }
            )
            async for message in ws:
                if message.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = message.json()
                if payload.get("type") != "event":
                    continue
                data = payload.get("data") or {}
                new_state = data.get("new_state")
                entity_id = data.get("entity_id")
                if not entity_id:
                    continue
                async with self._lock:
                    if new_state is None:
                        self._states.pop(entity_id, None)
                    else:
                        self._states[entity_id] = new_state
                self._notify_listeners()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def entity_flags(entity: dict[str, Any]) -> int:
        """Compute the capability bit flags for an entity."""
        domain = entity.get("entity_id", "").split(".", 1)[0]
        attributes = entity.get("attributes") or {}
        flags = EntityFlags.NONE

        if domain in {"light", "switch", "fan", "input_boolean", "humidifier"}:
            flags |= EntityFlags.TOGGLE
        if domain == "lock":
            flags |= EntityFlags.OPEN_CLOSE
        if domain == "cover":
            flags |= EntityFlags.TOGGLE | EntityFlags.OPEN_CLOSE
        if domain == "alarm_control_panel":
            flags |= EntityFlags.TOGGLE | EntityFlags.OPEN_CLOSE
        if domain == "climate":
            flags |= EntityFlags.TOGGLE | EntityFlags.SETPOINT
        if domain in {"scene", "script"}:
            flags |= EntityFlags.TOGGLE
        if domain == "remote":
            flags |= EntityFlags.TOGGLE
        if domain == "media_player":
            flags |= EntityFlags.TOGGLE
        if domain == "vacuum":
            flags |= EntityFlags.TOGGLE

        if "brightness" in attributes:
            flags |= EntityFlags.BRIGHTNESS
        if "percentage" in attributes:
            flags |= EntityFlags.PERCENT
        if domain == "climate":
            flags |= EntityFlags.SETPOINT
        if domain == "cover" and "current_position" in attributes:
            flags |= EntityFlags.LEVEL
        if attributes.get("friendly_name"):
            pass
        return int(flags)

    @staticmethod
    def entity_value(entity: dict[str, Any]) -> float | None:
        """Extract the most meaningful numeric value for an entity."""
        attributes = entity.get("attributes") or {}
        for key in _LEVEL_ATTRIBUTES:
            value = attributes.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    @staticmethod
    def is_exposed(domain: str) -> bool:
        """True when entities in this domain are useful on a watch."""
        return domain in CONTROLLABLE_DOMAINS
