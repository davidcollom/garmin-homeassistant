"""HTTP client for the Garmin bridge."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BridgeError(Exception):
    """Raised when the bridge cannot be reached or rejects a request."""


class BridgeClient:
    """Small async client for the bridge REST API."""

    def __init__(self, session: ClientSession, url: str, token: str) -> None:
        """Initialise the client."""
        self._session = session
        self._url = url.rstrip("/")
        self._token = token
        self._timeout = ClientTimeout(total=15)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
                timeout=self._timeout,
            ) as response:
                if response.status == 401:
                    raise BridgeError("The bridge rejected the access token")
                if response.status >= 400:
                    body = await response.text()
                    raise BridgeError(f"Bridge returned {response.status}: {body[:200]}")
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text()
        except ClientError as err:
            raise BridgeError(f"Could not reach the bridge at {self._url}: {err}") from err

    # -- read --------------------------------------------------------------

    async def async_health(self) -> dict[str, Any]:
        """Check that the bridge is reachable and healthy."""
        return await self._request("GET", "/v1/health")

    async def async_watches(self) -> list[dict[str, Any]]:
        """List the paired watches."""
        payload = await self._request("GET", "/v1/admin/watches")
        return list(payload.get("watches") or [])

    async def async_entities(self) -> list[dict[str, Any]]:
        """List the entities currently exposed to the watches."""
        payload = await self._request("GET", "/v1/admin/entities")
        return list(payload.get("entities") or [])

    async def async_config(self) -> dict[str, Any]:
        """Read the bridge configuration."""
        return await self._request("GET", "/v1/admin/config")

    # -- write -------------------------------------------------------------

    async def async_set_exposed(
        self,
        exposed: list[str] | None = None,
        blocked: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update which entities the watches can see."""
        payload: dict[str, Any] = {}
        if exposed is not None:
            payload["exposed_entities"] = exposed
        if blocked is not None:
            payload["blocked_entities"] = blocked
        return await self._request("POST", "/v1/admin/config", json=payload)

    async def async_notify(
        self,
        title: str,
        message: str,
        priority: str = "normal",
        actions: list[dict[str, str]] | None = None,
        entity_id: str | None = None,
        watch_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Queue a notification for the watches."""
        payload: dict[str, Any] = {"title": title, "body": message, "priority": priority}
        if actions:
            payload["actions"] = actions
        if entity_id:
            payload["entity_id"] = entity_id
        if watch_ids:
            payload["watch_ids"] = watch_ids
        return await self._request("POST", "/v1/admin/notify", json=payload)

    async def async_command(
        self,
        command: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a command through the bridge."""
        payload: dict[str, Any] = {"cmd": command, "data": data or {}}
        if entity_id:
            payload["entity_id"] = entity_id
        return await self._request("POST", "/v1/commands", json=payload)

    async def async_refresh(self) -> dict[str, Any]:
        """Ask the bridge to re-read the Home Assistant states."""
        return await self._request("POST", "/v1/admin/refresh")

    async def async_valid(self) -> bool:
        """Return True when the bridge accepts our credentials."""
        try:
            health = await self.async_health()
        except BridgeError as err:
            _LOGGER.debug("%s: bridge not reachable: %s", DOMAIN, err)
            return False
        return bool(health.get("ok"))
