# Troubleshooting

## The bridge does not start

The bridge refuses to start when the configuration is incomplete.  It prints
the problems on the standard error:

```text
error: HA_TOKEN is required (Home Assistant long-lived access token)
error: GARMIN_BRIDGE_TOKEN is required
```

Check the environment of the container, not the compose file, if you use an
`.env` file or a secrets manager.

## The Home Assistant integration cannot be set up

*Could not reach the bridge* means that the integration could not open a
connection or that the bridge refused the token.

1. Check the bridge from the Home Assistant host:

   ```bash
   curl -H "Authorization: Bearer <bridge token>" http://<bridge>:8099/v1/health
   ```

   A `200` with `{"ok": true}` means that the bridge is fine and the token
   is right.

2. A `401` means that the token in the integration does not match
   `GARMIN_BRIDGE_TOKEN`.

3. A connection error means that the address is wrong.  Use an address that
   Home Assistant can resolve, for example the service name of the
   container.

4. Check the log of the bridge.  It logs every failed request with the
   reason.

## The watch does not show any entity

Work through the chain from the bottom up.

### 1. The watch reaches the bridge

Open the application on the watch.  The *Status* screen shows the bridge
address and the connection state.

* *Set the bridge URL in Garmin Connect* means that the *Bridge URL* setting
  is empty.
* *Offline* means that the watch cannot reach the bridge.  Check that the
  address resolves on the watch: an IP address is more reliable than
  `homeassistant.local`.
* A `401` in the bridge log means that the *Bridge token* setting of the
  watch is wrong, or that the bridge was restarted and the token of the
  watch is no longer valid.

### 2. The watch is registered

```bash
curl -H "Authorization: Bearer <bridge token>" http://<bridge>:8099/v1/admin/watches
```

An empty list means that the watch never registered.  The registration
happens on the first start of the application.  If the watch has an id from
an earlier installation, remove it with:

```bash
curl -X DELETE -H "Authorization: Bearer <bridge token>" \
    http://<bridge>:8099/v1/admin/watches/<watch id>
```

and start the application again.

### 3. The bridge has entities

```bash
curl -H "Authorization: Bearer <bridge token>" http://<bridge>:8099/v1/admin/entities
```

An empty list means that either Home Assistant has no controllable entity
or that the exposure lists are too narrow.  Check:

* the `GARMIN_ENTITY_ALLOWLIST` of the bridge,
* the *exposed entities* option of the integration,
* the *blocked entities* option of the integration.

### 4. The bridge talks to Home Assistant

```bash
curl -H "Authorization: Bearer <bridge token>" http://<bridge>:8099/v1/health
```

The health route reports whether the bridge is connected to Home Assistant.

## The states on the watch are stale

The bridge mirrors the states through the Home Assistant websocket.  If the
websocket does not connect, the bridge falls back to the poll, which runs
every `GARMIN_POLL_INTERVAL` seconds.

Check the log of the bridge for websocket errors, and check that the
Home Assistant instance allows the connection.  A proxy that does not
support websockets is the usual cause.

## A command does nothing

The bridge answers with a short message that is shown on the watch:

| Message | Meaning |
| --- | --- |
| `No entity specified` | The command did not name an entity. |
| `Unsupported command: …` | The command is not one the bridge knows. |
| `401` or `403` | The Home Assistant token may not call that service. |
| `404` | The entity does not exist in Home Assistant. |

The bridge log has the full error of a failed service call.

## A notification does not arrive

1. Does the notification reach the bridge?

   ```bash
   curl -X POST -H "Authorization: Bearer <bridge token>" \
       -H "Content-Type: application/json" \
       -d '{"title":"Test","body":"Hello"}' \
       http://<bridge>:8099/v1/admin/notify
   ```

2. Is it in the queue of the watch?

   ```bash
   curl -H "Authorization: Bearer <watch token>" \
       -H "X-Garmin-Watch-Id: <watch id>" \
       http://<bridge>:8099/v1/notifications
   ```

3. A notification that is in the queue but that the watch does not show is
   a problem of the watch: the application only polls while it is in the
   foreground, or the background service is not allowed to run.  Check the
   battery optimisation of the phone and the watch.

## The phone does not receive the mirrored notifications

* The option *Phone notification service* has to name an existing notify
  service, for example `mobile_app_iphone`.
* The Garmin Connect app has to be installed and logged in.
* The phone has to be able to reach Home Assistant.

The mirroring is best effort: the bridge logs a warning when the phone
service fails.

## The action of a notification does not reach the automation

The bridge fires a `garmin_homeassistant_watch_action` event.  The event
carries the `watch_id`, the `notification_id`, the `action` and, when the
notification was about an entity, the `entity_id`.

In the automation, the data of the event is under `trigger.event.data`:

```yaml
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.action == 'open' }}"
```

## The application does not build

* `monkeyc was not found` — the Connect IQ SDK is not installed or
  `MONKEYC` does not point at it.
* A module is missing — the device does not implement it.  See
  [`device-support.md`](device-support.md).
* The application is too big — the Edge 1040 has less memory than the Venu
  4.  Check the build log for the size of the application.

## Getting more information

| Where | What it shows |
| --- | --- |
| The log of the bridge | Every request, every failed call to Home Assistant. |
| The log of Home Assistant | The integration, the services and the events. |
| The *Status* screen of the watch | The bridge address, the connection state and the last error. |
| `GET /v1/health` | The state of the bridge and of the connection to Home Assistant. |
