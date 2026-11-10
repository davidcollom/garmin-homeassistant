# Architecture

Garmin Home Assistant is made of three independent programs.  Each one can be
replaced on its own, and each one only knows about its direct neighbours.

```text
┌──────────────────────────┐
│  Garmin watch            │
│  Connect IQ application  │
│  (watch/)                │
└────────────┬─────────────┘
             │ HTTP + JSON over the local network
             │ Authorization: Bearer <watch token>
             │ X-Garmin-Watch-Id: <watch id>
┌────────────▼─────────────┐
│  Bridge                  │
│  FastAPI service         │
│  (bridge/)               │
└────────────┬─────────────┘
             │ Home Assistant REST API + websocket
             │ Authorization: Bearer <long lived access token>
┌────────────▼─────────────┐
│  Home Assistant          │
│  custom_components/      │
│  garmin_homeassistant    │
└──────────────────────────┘
```

## Why a bridge at all?

The watch could talk to Home Assistant directly, but then every watch would
need a Home Assistant long-lived access token, and the token would live on a
device with no way to protect it.  The bridge keeps the secret:

* The **bridge** holds the Home Assistant long-lived access token.  It never
  leaves the bridge.
* The **watch** holds a token that only allows the watch routes of the
  bridge.  The bridge issues it when the watch registers.
* The **Home Assistant integration** holds the bridge token, which only
  allows the admin routes.

That way, a lost watch can be removed from the bridge without touching the
Home Assistant token, and a leaked watch token does not grant access to
Home Assistant.

## The bridge

The bridge is a single FastAPI process.  It has no database and no cache on
disk: everything it knows is in memory and is rebuilt from Home Assistant
when it restarts.

### Home Assistant client

`bridge/src/garmin_bridge/ha.py` keeps a live mirror of the Home Assistant
state:

* A **websocket subscription** to `state_changed` events, so the mirror
  reacts immediately when something changes in Home Assistant.
* A **slow poll** of `GET /api/states` every `GARMIN_POLL_INTERVAL` seconds
  as a safety net, in case the websocket drops.

The area registry is read from `GET /api/areas` so the watch can group the
entities the way Home Assistant does.

Service calls go to `POST /api/services/<domain>/<service>`.

### Entity store

`bridge/src/garmin_bridge/store.py` holds the entities in the compact format
that the watch understands, together with a monotonically increasing
revision.  Every time the state of an entity changes, the revision goes up.
The watch sends the revision it already knows, and the bridge answers with
the difference, so a poll after a long pause costs almost nothing.

The change log has a bounded size.  When it no longer reaches back to the
revision a watch sent, the bridge answers with a full snapshot instead.

### Watch registry

The registry maps a watch id to its token, its last contact and the
telemetry it reported (battery, steps, heart rate).  A watch that has not
been seen for `GARMIN_WATCH_STALE_AFTER` seconds counts as offline.

### Notification queue

The queue holds the notifications that Home Assistant sent.  Every watch has
its own cursor, so a notification that one watch acknowledged is still
waiting for the other one.  A notification is dropped once every watch has
acknowledged it or once the queue overflows.

### Command executor

`bridge/src/garmin_bridge/commands.py` translates a compact command such as
`toggle` into the Home Assistant service that fits the domain of the entity.
A lock is unlocked when it is locked and locked when it is not, a cover is
opened when it is closed, and so on.  The answer is short enough to fit on a
watch screen.

## The watch application

The watch application is a Connect IQ program written in Monkey C.  It has
three screens:

* **Entities** – the list of the entities the bridge exposes, grouped by
  area.  Tap an entity to see its state and the actions it supports.
* **Inbox** – the notifications that Home Assistant sent.
* **Status** – the connection state, the bridge address and the battery of
  the watch.

The application polls the bridge while it is in the foreground.  The
background service only refreshes the notification queue, because the
Edge 1040 only offers 32 KB of memory for a background
service.  See [`device-support.md`](device-support.md) for the details.

### Capability detection

`watch/source/Capabilities.mc` asks the device what it can do through
`Toybox.System.getDeviceSettings()`.  The application uses the answer to
decide whether it may raise a system notification with
`Toybox.Notifications`, how much memory it may use and which resources are
safe to touch.

The build itself is split in two as well.  The Venu 4 build uses the
presenter in `watch/variants/notifications`, the Edge 1040
build uses the presenter in `watch/variants/toast`.  Everything else is
shared, so the two devices cannot drift apart.

## The Home Assistant integration

The integration is a normal custom integration with a config flow.  It

* polls the bridge for the watches and their telemetry,
* creates the entities of every watch,
* registers the services,
* loads the `notify` platform, which registers
  `notify.garmin_homeassistant`.

The notification service queues the message on the bridge and, when a phone
notification service is configured, mirrors it there so that the Garmin
Connect app pushes it to the wrist.

## The data flow

### Reading the entities

```text
watch  ──GET /v1/entities?since=42──────────►  bridge
watch  ◄──{"ts":…, "rev":43, "areas":[…], "e":[[…]]}──
```

### Running a command

```text
watch  ──POST /v1/commands {"cmd":"toggle","entity_id":"light.kitchen"}──►  bridge
bridge ──POST /api/services/light/turn_on ──►  Home Assistant
watch  ◄──{"ok":true,"message":"light.turn_on","state":"on"}──────────────
```

### Sending a notification

```text
Home Assistant ──POST /v1/admin/notify──►  bridge
watch ──GET /v1/notifications──────────►  bridge
watch ◄──{"notifications":[…]}─────────────
watch ──POST /v1/notifications/<id>/ack──►  bridge
```

## The compact wire format

A watch has little memory and the connection is slow, so the payloads are
small.  An entity is a seven element array instead of an object:

```json
["light.kitchen", "Kitchen", "light", "on", 3, 0, 128.0]
```

| Index | Meaning |
| --- | --- |
| 0 | Entity id |
| 1 | Name |
| 2 | Domain |
| 3 | State |
| 4 | Flags |
| 5 | Index into the area table, `-1` when there is none |
| 6 | Numeric value, for example a brightness |

The flags tell the watch what it may do with the entity:

| Flag | Value | Meaning |
| --- | --- | --- |
| `TOGGLE` | 1 | The entity can be switched on and off. |
| `BRIGHTNESS` | 2 | The entity has a brightness attribute. |
| `LEVEL` | 4 | The entity has a numeric level. |
| `OPEN_CLOSE` | 8 | The entity opens and closes. |
| `SETPOINT` | 16 | The entity has a setpoint, for example a temperature. |
| `PINNED` | 32 | The entity is pinned to the top of the list. |
| `PERCENT` | 64 | The numeric value is a percentage. |

## Request bodies

Connect IQ runtimes older than 6.0.3 cannot send a JSON body, so the bridge
accepts four shapes and normalises them to JSON before it validates them:

* a normal `application/json` body,
* a form field named `json` that holds the JSON document,
* plain form fields,
* a `json` query parameter.

That keeps the watch application working on old runtimes without giving up
the compact format on the new ones.
