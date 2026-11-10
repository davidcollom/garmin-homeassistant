"""Environment-driven configuration for the bridge.

Configuration is intentionally flat and environment-only so the bridge can run
as a single container with no config file to mount.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ValueError(f"{name} must be a boolean, got {raw!r}")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _env_list(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _env_tokens(name: str) -> dict[str, str]:
    """Parse a JSON object of ``watch_id: token`` pairs."""
    raw = os.getenv(name)
    if not raw:
        return {}
    import json

    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a JSON object, got {raw!r}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}


@dataclass(slots=True)
class BridgeConfig:
    """Runtime configuration.

    Attributes:
        home_assistant_url: Base URL of Home Assistant, e.g. ``http://homeassistant:8123``.
        home_assistant_token: Long-lived access token used for the HA REST API.
        bridge_token: Token the Home Assistant integration uses to talk to the bridge.
        watch_token: Token the watch app uses. Defaults to ``bridge_token``.
        host: Interface the bridge binds to.
        port: Port the bridge binds to.
        poll_interval: Seconds between Home Assistant state reconciliations.
        stale_after: Seconds after which a watch is considered offline.
        entity_allowlist: Optional list of entity ids exposed to watches.
        entity_blocklist: Entity ids never exposed to watches.
        log_level: Python logging level.
        cors_origins: Origins allowed to call the admin API from a browser.
    """

    home_assistant_url: str = field(
        default_factory=lambda: os.getenv("HA_URL", "http://homeassistant:8123")
    )
    home_assistant_token: str = field(default_factory=lambda: os.getenv("HA_TOKEN", ""))
    bridge_token: str = field(default_factory=lambda: os.getenv("GARMIN_BRIDGE_TOKEN", ""))
    watch_token: str = field(default_factory=lambda: os.getenv("GARMIN_WATCH_TOKEN", ""))
    watch_tokens: dict[str, str] = field(default_factory=lambda: _env_tokens("GARMIN_WATCH_TOKENS"))
    host: str = field(default_factory=lambda: os.getenv("GARMIN_BRIDGE_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("GARMIN_BRIDGE_PORT", 8099))
    poll_interval: int = field(default_factory=lambda: _env_int("GARMIN_POLL_INTERVAL", 30))
    stale_after: int = field(default_factory=lambda: _env_int("GARMIN_WATCH_STALE_AFTER", 900))
    entity_allowlist: tuple[str, ...] = field(
        default_factory=lambda: _env_list("GARMIN_ENTITY_ALLOWLIST")
    )
    entity_blocklist: tuple[str, ...] = field(
        default_factory=lambda: _env_list("GARMIN_ENTITY_BLOCKLIST")
    )
    log_level: str = field(default_factory=lambda: os.getenv("GARMIN_LOG_LEVEL", "INFO"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: _env_list("GARMIN_CORS_ORIGINS"))

    def __post_init__(self) -> None:
        self.home_assistant_url = self.home_assistant_url.rstrip("/")
        if not self.watch_token:
            self.watch_token = self.bridge_token

    @property
    def valid(self) -> list[str]:
        """Return a list of configuration problems; empty when the config is usable."""
        problems: list[str] = []
        if not self.home_assistant_token:
            problems.append("HA_TOKEN is required (Home Assistant long-lived access token)")
        if not self.bridge_token:
            problems.append("GARMIN_BRIDGE_TOKEN is required")
        if not self.watch_token:
            problems.append("GARMIN_WATCH_TOKEN is required")
        return problems


def load_config() -> BridgeConfig:
    """Build a :class:`BridgeConfig` from the process environment."""
    return BridgeConfig()
