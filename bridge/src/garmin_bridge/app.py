"""FastAPI application exposing the bridge API."""

import json
import logging
import time
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Annotated, Any
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from . import __version__
from .commands import CommandExecutor
from .config import BridgeConfig, load_config
from .ha import HomeAssistantClient
from .models import (
    CommandRequest,
    CommandResponse,
    CompactEntity,
    EntitySnapshot,
    HealthResponse,
    NotificationAck,
    NotificationAction,
    NotificationList,
    WatchConfig,
    WatchEvent,
    WatchList,
    WatchRegistration,
    WatchRegistrationResponse,
)
from .store import EntityStore, NotificationQueue, WatchRegistry

_LOGGER = logging.getLogger(__name__)

WATCH_ID_HEADER = "X-Garmin-Watch-Id"

#: Home Assistant event that is fired when a watch picks a notification action.
EVENT_WATCH_ACTION = "garmin_homeassistant_watch_action"


class JsonRoute(APIRoute):
    """Route that understands the request bodies a Connect IQ watch can send.

    Connect IQ runtimes before 6.0.3 have no ``:body`` option, so a POST is
    sent form encoded.  Newer runtimes send proper JSON.  This route accepts
    all of these:

    * a regular ``application/json`` body,
    * a form field named ``json`` that holds the JSON document,
    * plain form fields, and
    * a ``json`` query parameter.

    The payload is normalised to JSON before FastAPI validates it, so the
    handlers only ever see one shape.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            await _normalise_body(request)
            return await original_route_handler(request)

        return custom_route_handler


async def _normalise_body(request: Request) -> None:
    """Rewrite a non JSON request body into JSON when possible.

    The body is parsed by hand instead of with the form parser so that the
    bridge does not need an extra dependency for one content type.
    """
    if "json" in request.headers.get("content-type", ""):
        return

    raw = request.query_params.get("json")
    if raw is None:
        body = await request.body()
        if not body:
            return
        text = body.decode("utf-8", "replace")
        fields = dict(parse_qsl(text))
        raw = fields.get("json")
        if raw is None:
            if not fields:
                # Not a form body either; try to read it as plain JSON.
                raw = text
            else:
                _set_json_body(request, fields)
                return

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return
    if isinstance(payload, dict):
        _set_json_body(request, payload)


def _set_json_body(request: Request, payload: dict[str, Any]) -> None:
    """Replace the request body with a JSON document."""
    body = json.dumps(payload).encode("utf-8")
    # Starlette caches the raw body on the request object.
    request._body = body  # noqa: SLF001
    # The content type has to change as well, otherwise FastAPI keeps
    # treating the payload as an opaque blob.
    headers = [
        (key, value)
        for key, value in request.scope.get("headers", [])
        if key.lower() != b"content-type"
    ]
    headers.append((b"content-type", b"application/json"))
    request.scope["headers"] = headers
    if hasattr(request, "_headers"):
        del request._headers  # noqa: SLF001


class BridgeState:
    """Holds the live objects shared by the routes."""

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self._ha = HomeAssistantClient(
            config.home_assistant_url,
            config.home_assistant_token,
            poll_interval=config.poll_interval,
        )
        self.executor = CommandExecutor(self._ha)
        self.entities = EntityStore()
        self.watches = WatchRegistry(stale_after=config.stale_after)
        self.notifications = NotificationQueue()
        self.started_at = int(time.time())
        #: Entity ids the bridge may expose at all.  ``None`` means that
        #: every controllable entity may be exposed.
        self.base_exposed_entities: tuple[str, ...] | None = (
            tuple(config.entity_allowlist) if config.entity_allowlist else None
        )
        #: Entity ids the Home Assistant integration selected.  An empty list
        #: means "everything the base list allows".
        self.exposed_entities: list[str] = []
        #: Entity ids the bridge never exposes, whatever else is configured.
        self.base_blocked_entities: list[str] = list(config.entity_blocklist)
        #: Entity ids the Home Assistant integration blocked.
        self.blocked_entities: list[str] = []

    @property
    def ha(self) -> HomeAssistantClient:
        """The Home Assistant client."""
        return self._ha

    @ha.setter
    def ha(self, client: HomeAssistantClient) -> None:
        """Replace the client; the command executor follows along."""
        self._ha = client
        self.executor = CommandExecutor(client)

    async def start(self) -> None:
        await self.ha.start()
        self.ha.add_listener(self._sync_entities)

    async def stop(self) -> None:
        await self.ha.stop()

    def _sync_entities(self) -> None:
        changed = self.entities.sync(
            self.ha.states,
            self.ha.areas,
            self.effective_allowlist(),
            self.effective_blocklist(),
        )
        if changed:
            _LOGGER.debug("Entity mirror updated: %s entities changed", changed)

    def effective_allowlist(self) -> list[str] | None:
        """Return the entity ids the watches may see.

        The base list of the bridge is the outer limit and the selection of
        the integration narrows it down.  ``None`` means that there is no
        limit at all, an empty list means that nothing is exposed.
        """
        base = self.base_exposed_entities
        selected = self.exposed_entities
        if base is None:
            return list(selected) if selected else None
        if not selected:
            return list(base)
        chosen = set(selected)
        return [entity_id for entity_id in base if entity_id in chosen]

    def effective_blocklist(self) -> list[str]:
        """Return the entity ids that are never exposed."""
        blocked = list(self.base_blocked_entities)
        for entity_id in self.blocked_entities:
            if entity_id not in blocked:
                blocked.append(entity_id)
        return blocked

    async def refresh(self) -> None:
        await self.ha.refresh()
        self._sync_entities()


def create_app(config: BridgeConfig | None = None) -> FastAPI:
    """Build the FastAPI application."""
    cfg = config or load_config()
    state = BridgeState(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        problems = cfg.valid
        if problems:
            _LOGGER.error("Incomplete configuration: %s", "; ".join(problems))
        else:
            await state.start()
        try:
            yield
        finally:
            await state.stop()

    app = FastAPI(
        title="Garmin Home Assistant Bridge",
        description=(
            "Bridges Garmin Connect IQ watches to Home Assistant. "
            "Watches reach this service through the paired phone using "
            "Toybox.Communications.makeWebRequest()."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    # Connect IQ cannot always send a JSON body, so every route learns to
    # accept the form encoded variants as well.
    app.router.route_class = JsonRoute
    app.state.bridge = state

    if cfg.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cfg.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # -- authentication ----------------------------------------------------

    def _check(token: str | None, expected: str) -> bool:
        return bool(expected) and token is not None and token == expected

    async def require_any(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        """Accept the bridge token, the shared watch token or a watch token.

        A watch is allowed to use

        * the shared ``GARMIN_WATCH_TOKEN``,
        * a token pinned to it in ``GARMIN_WATCH_TOKENS``, or
        * the token the bridge handed out when the watch registered.
        """
        token = _extract_bearer(authorization)
        if _check(token, cfg.bridge_token) or _check(token, cfg.watch_token):
            return
        watch_id = request.headers.get(WATCH_ID_HEADER)
        if watch_id and token:
            if _check(token, cfg.watch_tokens.get(watch_id, "")):
                return
            issued = state.watches.token(watch_id)
            if issued and token == issued:
                return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    async def require_admin(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        """Accept only the bridge token."""
        token = _extract_bearer(authorization)
        if not _check(token, cfg.bridge_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    def _extract_bearer(authorization: str | None) -> str | None:
        if not authorization:
            return None
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return None

    def _watch_id(request: Request) -> str:
        return request.headers.get(WATCH_ID_HEADER) or "default"

    # -- watch facing API --------------------------------------------------

    @app.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Basic connectivity check. Deliberately unauthenticated."""
        return HealthResponse(
            ok=True,
            version=__version__,
            ha_connected=state.ha.connected,
            entities=len(state.entities.all_entities()),
            watches=len(state.watches.all()),
        )

    @app.get("/v1/config", response_model=WatchConfig)
    async def watch_config(_: Annotated[None, Depends(require_any)]) -> WatchConfig:
        """Settings the watch app should honour."""
        return WatchConfig(
            poll_interval=max(10, cfg.poll_interval // 2),
            background_interval=max(300, cfg.poll_interval * 30),
            page_size=25,
        )

    @app.post("/v1/watches/register", response_model=WatchRegistrationResponse)
    async def register_watch(
        _: Annotated[None, Depends(require_any)],
        registration: WatchRegistration,
        request: Request,
    ) -> WatchRegistrationResponse:
        """Register or refresh a paired watch.

        The response carries a token that is bound to this watch.  The watch
        stores it and uses it from then on, so the shared bootstrap token
        only has to be configured once.
        """
        watch = state.watches.register(
            watch_id=registration.watch_id,
            name=registration.name,
            model=registration.model,
            api_level=registration.api_level,
            capabilities=registration.capabilities,
        )
        token = state.watches.issue_token(registration.watch_id)
        state.notifications.ensure_watch(registration.watch_id)
        _LOGGER.info(
            "Watch registered: %s (%s)", registration.name, registration.model or "unknown model"
        )
        return WatchRegistrationResponse(**watch.model_dump(), token=token)

    @app.get("/v1/watches", response_model=WatchList)
    async def list_watches(_: Annotated[None, Depends(require_any)]) -> WatchList:
        """List paired watches."""
        return WatchList(watches=state.watches.all())

    @app.get("/v1/entities", response_model=EntitySnapshot)
    async def list_entities(
        _: Annotated[None, Depends(require_any)],
        request: Request,
        since: Annotated[int, Query(ge=0)] = 0,
        ids: Annotated[str | None, Query()] = None,
        limit: Annotated[int | None, Query(ge=0)] = None,
        offset: Annotated[int, Query(ge=0)] = 0,
        verbose: Annotated[bool, Query()] = False,
    ) -> Any:
        """Return the controllable entity snapshot.

        ``since`` returns only entities changed after that revision, which keeps
        the payload small on a busy Home Assistant instance.  Entities that
        disappeared are reported in ``r`` so the watch can drop them.

        ``limit`` and ``offset`` page through the result set.  ``n`` is the
        total number of matching entities and ``more`` tells the watch whether
        another page follows.
        """
        entity_ids = None
        if ids:
            entity_ids = [item.strip() for item in ids.split(",") if item.strip()]
        removed: list[str] = []
        if since:
            changed = state.entities.changed_since(since)
            removed = state.entities.removed_since(since)
            if changed:
                entity_ids = changed if entity_ids is None else list(set(entity_ids) & set(changed))
            elif entity_ids is None:
                entity_ids = []
        snapshot = state.entities.snapshot(
            entity_ids,
            limit=limit,
            offset=offset,
            removed=removed,
        )
        if verbose:
            return {
                "ts": snapshot.ts,
                "rev": snapshot.rev,
                "areas": snapshot.areas,
                "entities": state.entities.verbose_entities(),
            }
        return snapshot

    @app.get("/v1/entities/{entity_id}", response_model=CompactEntity)
    async def get_entity(
        _: Annotated[None, Depends(require_any)],
        entity_id: str,
    ) -> CompactEntity:
        """Return a single entity."""
        entity = state.entities.entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown entity")
        return entity

    @app.post("/v1/commands", response_model=CommandResponse)
    async def run_command(
        _: Annotated[None, Depends(require_any)],
        command: CommandRequest,
        request: Request,
    ) -> CommandResponse:
        """Execute a command against Home Assistant."""
        watch_id = _watch_id(request)
        state.watches.touch(watch_id)
        return await state.executor.execute(command)

    @app.get("/v1/notifications", response_model=NotificationList)
    async def list_notifications(
        _: Annotated[None, Depends(require_any)],
        request: Request,
        since: Annotated[int, Query(ge=0)] = 0,
    ) -> NotificationList:
        """Return notifications queued for this watch.

        The response always contains every notification that has not been
        acknowledged yet.  ``cursor`` is an opaque sequence number the watch
        can send back as ``since``.
        """
        watch_id = _watch_id(request)
        state.watches.touch(watch_id)
        pending = state.notifications.pending(watch_id)
        return NotificationList(
            ts=int(time.time()),
            cursor=state.notifications.cursor(watch_id),
            n=pending,
        )

    @app.post("/v1/notifications/{notification_id}/ack", response_model=CommandResponse)
    async def acknowledge_notification(
        _: Annotated[None, Depends(require_any)],
        notification_id: str,
        ack: NotificationAck,
        request: Request,
    ) -> CommandResponse:
        """Acknowledge a notification and forward any chosen action to Home Assistant."""
        watch_id = _watch_id(request)
        notification = state.notifications.notification(watch_id, notification_id)
        found = state.notifications.acknowledge(watch_id, notification_id, ack.action)
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown notification"
            )
        if ack.action:
            data: dict[str, Any] = {
                "watch_id": watch_id,
                "notification_id": notification_id,
                "action": ack.action,
            }
            if notification is not None and notification.entity_id:
                data["entity_id"] = notification.entity_id
            await _fire_ha_event(state, EVENT_WATCH_ACTION, data)
        return CommandResponse(ok=True, message="acknowledged")

    @app.post("/v1/events", response_model=CommandResponse)
    async def watch_event(
        _: Annotated[None, Depends(require_any)],
        event: WatchEvent,
        request: Request,
    ) -> CommandResponse:
        """Receive telemetry or a button press from a watch."""
        watch_id = _watch_id(request)
        state.watches.touch(watch_id)
        if event.type == "telemetry":
            state.watches.update_telemetry(
                watch_id,
                battery=event.battery,
                steps=event.steps,
                heart_rate=event.heart_rate,
            )
        elif event.type == "button" and event.button:
            await _fire_ha_event(
                state,
                "garmin_watch_button",
                {"watch_id": watch_id, "button": event.button, "message": event.message or ""},
            )
        return CommandResponse(ok=True, message="ok")

    # -- admin API ---------------------------------------------------------

    @app.get("/v1/admin/entities")
    async def admin_entities(_: Annotated[None, Depends(require_admin)]) -> dict[str, Any]:
        """Full verbose entity list used by the Home Assistant integration."""
        return {
            "rev": state.entities.revision,
            "areas": state.entities.snapshot().areas,
            "entities": state.entities.verbose_entities(),
        }

    @app.get("/v1/admin/watches", response_model=WatchList)
    async def admin_watches(_: Annotated[None, Depends(require_admin)]) -> WatchList:
        """All paired watches including offline ones."""
        return WatchList(watches=state.watches.all())

    @app.post("/v1/admin/notify")
    async def admin_notify(
        _: Annotated[None, Depends(require_admin)],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Queue a notification for the watches."""
        actions = [
            NotificationAction(id=str(item.get("id", "")), label=str(item.get("label", "")))
            for item in payload.get("actions") or []
        ]
        watch_ids = payload.get("watch_ids")
        created = state.notifications.publish(
            title=str(payload.get("title", "Home Assistant")),
            body=str(payload.get("body", "")),
            priority=str(payload.get("priority", "normal")),
            actions=actions,
            entity_id=payload.get("entity_id"),
            watch_ids=watch_ids,
        )
        return {"queued": len(created), "ids": [n.id for n in created]}

    @app.post("/v1/admin/refresh")
    async def admin_refresh(_: Annotated[None, Depends(require_admin)]) -> dict[str, Any]:
        """Force a Home Assistant state refresh."""
        await state.refresh()
        return {"ok": True, "rev": state.entities.revision}

    @app.get("/v1/admin/config")
    async def admin_get_config(_: Annotated[None, Depends(require_admin)]) -> dict[str, Any]:
        """Current bridge configuration relevant to the integration."""
        return {
            "exposed_entities": list(state.exposed_entities),
            "blocked_entities": list(state.blocked_entities),
            "base_exposed_entities": list(state.base_exposed_entities or []),
            "base_blocked_entities": list(state.base_blocked_entities),
            "poll_interval": cfg.poll_interval,
            "stale_after": cfg.stale_after,
        }

    @app.post("/v1/admin/config")
    async def admin_set_config(
        _: Annotated[None, Depends(require_admin)],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Update which entities are exposed to the watches."""
        if "exposed_entities" in payload:
            state.exposed_entities = [str(item) for item in payload["exposed_entities"] or []]
        if "blocked_entities" in payload:
            state.blocked_entities = [str(item) for item in payload["blocked_entities"] or []]
        state._sync_entities()  # noqa: SLF001 - internal refresh, deliberate
        return {
            "exposed_entities": list(state.exposed_entities),
            "blocked_entities": list(state.blocked_entities),
            "base_exposed_entities": list(state.base_exposed_entities or []),
            "base_blocked_entities": list(state.base_blocked_entities),
            "rev": state.entities.revision,
        }

    @app.delete("/v1/admin/watches/{watch_id}")
    async def admin_delete_watch(
        _: Annotated[None, Depends(require_admin)],
        watch_id: str,
    ) -> dict[str, Any]:
        """Forget a paired watch."""
        removed = state.watches.remove(watch_id)
        return {"removed": removed}

    return app


async def _fire_ha_event(state: BridgeState, event_type: str, data: dict[str, Any]) -> None:
    """Fire a Home Assistant event so automations can react to watch actions."""
    try:
        await state.ha._request(  # noqa: SLF001 - internal helper, deliberate
            "POST",
            f"/api/events/{event_type}",
            json={"event_type": event_type, "data": data},
        )
    except Exception as exc:  # pragma: no cover - network dependent
        _LOGGER.warning("Could not fire Home Assistant event %s: %s", event_type, exc)


def main() -> None:  # pragma: no cover - entry point
    """Run the bridge with uvicorn."""
    import uvicorn

    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    uvicorn.run(
        create_app(cfg),
        host=cfg.host,
        port=cfg.port,
        log_level=cfg.log_level.lower(),
    )
