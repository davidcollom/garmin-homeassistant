# Garmin Home Assistant bridge

The bridge is a small FastAPI service that sits between the
[Connect IQ watch app](../watch) and [Home Assistant](../custom_components/garmin_homeassistant).

It does three things:

1. It keeps a live mirror of the Home Assistant entity states, so the watch
   always gets an answer without waiting for Home Assistant.
2. It translates the compact commands of the watch into Home Assistant
   service calls.
3. It queues the notifications that Home Assistant sends to the watch and
   hands them out when the watch polls.

The bridge holds the Home Assistant long-lived access token.  The watch never
sees it, and the Garmin cloud is not involved at all.

## Running it

### With Docker

```bash
docker build -t garmin-homeassistant-bridge:latest ..
docker run -d --name garmin-bridge \
    -p 8099:8099 \
    -e HA_URL=http://homeassistant:8123 \
    -e HA_TOKEN=... \
    -e GARMIN_BRIDGE_TOKEN=... \
    -e GARMIN_WATCH_TOKEN=... \
    garmin-homeassistant-bridge:latest
```

The repository root has a `docker-compose.yml` with the same settings.

### Without Docker

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
export HA_URL=http://homeassistant:8123
export HA_TOKEN=...
export GARMIN_BRIDGE_TOKEN=...
export GARMIN_WATCH_TOKEN=...
garmin-bridge
```

The service listens on `0.0.0.0:8099` by default.

## Configuration

Every setting is an environment variable.  The container needs no
configuration file.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HA_URL` | `http://homeassistant:8123` | Base URL of Home Assistant as seen from the bridge. |
| `HA_TOKEN` | – | Long-lived access token of Home Assistant.  Required. |
| `GARMIN_BRIDGE_TOKEN` | – | Token the Home Assistant integration uses.  Required. |
| `GARMIN_WATCH_TOKEN` | `GARMIN_BRIDGE_TOKEN` | Bootstrap token the watch uses on the first registration. |
| `GARMIN_WATCH_TOKENS` | – | JSON object with a token per watch id. |
| `GARMIN_BRIDGE_HOST` | `0.0.0.0` | Interface the bridge binds to. |
| `GARMIN_BRIDGE_PORT` | `8099` | Port the bridge listens on. |
| `GARMIN_POLL_INTERVAL` | `30` | Seconds between two reconciliations of the Home Assistant states. |
| `GARMIN_WATCH_STALE_AFTER` | `900` | Seconds after which a watch counts as offline. |
| `GARMIN_ENTITY_ALLOWLIST` | – | Comma separated entity ids that are exposed to the watches. |
| `GARMIN_ENTITY_BLOCKLIST` | – | Comma separated entity ids that are never exposed. |
| `GARMIN_CORS_ORIGINS` | – | Comma separated origins that may call the admin API from a browser. |
| `GARMIN_LOG_LEVEL` | `INFO` | Log level of the service. |

The bridge refuses to start without `HA_TOKEN` and `GARMIN_BRIDGE_TOKEN`.

## The API

All routes are versioned under `/v1`.  The watch routes accept the watch
token, the admin routes accept the bridge token.

### Watch routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | Liveness probe.  No token needed. |
| `GET` | `/v1/config` | The settings the watch needs (poll interval, stale timeout). |
| `POST` | `/v1/watches/register` | Register the watch and exchange the bootstrap token for a per-watch token. |
| `GET` | `/v1/watches` | The list of the registered watches. |
| `GET` | `/v1/entities` | The compact entity snapshot, paged. |
| `GET` | `/v1/entities/{entity_id}` | One entity in the compact format. |
| `POST` | `/v1/commands` | Run a command. |
| `GET` | `/v1/notifications` | The notifications that were not acknowledged yet. |
| `POST` | `/v1/notifications/{id}/ack` | Acknowledge a notification, optionally with an action. |
| `POST` | `/v1/events` | Report a watch event, for example a button press. |

### Admin routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/admin/entities` | The entities in the verbose format. |
| `GET` | `/v1/admin/watches` | The registered watches with their state. |
| `POST` | `/v1/admin/notify` | Queue a notification. |
| `POST` | `/v1/admin/refresh` | Re-read the Home Assistant states right away. |
| `GET` | `/v1/admin/config` | Read the exposure configuration. |
| `POST` | `/v1/admin/config` | Write the exposure configuration. |
| `DELETE` | `/v1/admin/watches/{watch_id}` | Forget a watch. |

### Authentication

The bridge uses bearer tokens:

```http
Authorization: Bearer <token>
```

The watch sends its own token in the `Authorization` header and its id in the
`X-Garmin-Watch-Id` header.  The Home Assistant integration sends the bridge
token.

A request without a token gets `401`.  A request with a token that is not
allowed to use the route gets `403`.

### Compact wire format

The watch has little memory and the connection to the bridge is slow, so the
payloads are compact.  An entity is a seven element array:

```json
["light.kitchen", "Kitchen", "light", "on", 3, 0, 128.0]
```

| Index | Meaning |
| --- | --- |
| 0 | Entity id |
| 1 | Name |
| 2 | Domain |
| 3 | State |
| 4 | Flags, a bit mask |
| 5 | Index into the area table, `-1` when there is none |
| 6 | Numeric value, for example a brightness |

The flags tell the watch what it can do with the entity:

| Flag | Value | Meaning |
| --- | --- | --- |
| `TOGGLE` | 1 | The entity can be switched on and off. |
| `BRIGHTNESS` | 2 | The entity has a brightness attribute. |
| `LEVEL` | 4 | The entity has a numeric level. |
| `OPEN_CLOSE` | 8 | The entity opens and closes. |
| `SETPOINT` | 16 | The entity has a setpoint, for example a temperature. |
| `PINNED` | 32 | The entity is pinned to the top of the list. |
| `PERCENT` | 64 | The numeric value is a percentage. |

A notification is an object with `id`, `ts`, `title`, `body`, `priority`,
`actions` and `entity_id`.

### Request bodies

Connect IQ runtimes older than 6.0.3 cannot send a JSON body.  The bridge
therefore accepts a JSON body, a form field named `json` that holds the JSON
document, plain form fields and a `json` query parameter.  Everything is
normalised to JSON before it is validated.

## Development

```bash
pip install -e ".[test]"
pytest tests -q
ruff check src tests
mypy src
```

The tests use a fake Home Assistant, so they need neither a real Home
Assistant nor a network connection.
