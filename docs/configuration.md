# Configuration

Every part of Garmin Home Assistant is configured on its own: the bridge with
environment variables, the Home Assistant integration through its options
flow and the watch application through its own settings.

## The bridge

The bridge is configured with environment variables only, so it can run as a
single container without a configuration file.

| Variable | Default | Description |
| --- | --- | --- |
| `HA_URL` | `http://homeassistant:8123` | Base URL of Home Assistant as seen from the bridge.  A trailing slash is removed. |
| `HA_TOKEN` | – | Long-lived access token of Home Assistant.  **Required.** |
| `GARMIN_BRIDGE_TOKEN` | – | Token the Home Assistant integration uses.  **Required.** |
| `GARMIN_WATCH_TOKEN` | `GARMIN_BRIDGE_TOKEN` | Bootstrap token the watch app uses for the first registration. |
| `GARMIN_WATCH_TOKENS` | – | JSON object that maps a watch id to a token, for example `{"edge1040-1a2b3c":"secret"}`.  A watch may use either its own token or the bootstrap token. |
| `GARMIN_BRIDGE_HOST` | `0.0.0.0` | Interface the bridge binds to.  Use `127.0.0.1` to keep it local. |
| `GARMIN_BRIDGE_PORT` | `8099` | Port the bridge listens on. |
| `GARMIN_POLL_INTERVAL` | `30` | Seconds between two reconciliations of the Home Assistant states.  The websocket reacts immediately, the poll is only a safety net. |
| `GARMIN_WATCH_STALE_AFTER` | `900` | Seconds after which a watch counts as offline. |
| `GARMIN_ENTITY_ALLOWLIST` | – | Comma separated entity ids that are exposed to the watches.  When it is empty every controllable entity is exposed. |
| `GARMIN_ENTITY_BLOCKLIST` | – | Comma separated entity ids that are never exposed, even when the allow list would allow them. |
| `GARMIN_CORS_ORIGINS` | – | Comma separated origins that may call the admin API from a browser.  Leave it empty if nothing but Home Assistant talks to the bridge. |
| `GARMIN_LOG_LEVEL` | `INFO` | Log level of the service.  Use `DEBUG` to see every request. |

### Example

```bash
HA_URL=http://homeassistant.local:8123
HA_TOKEN=eyJhbGciOi...
GARMIN_BRIDGE_TOKEN=K8v3Nq1s...
GARMIN_WATCH_TOKEN=Zx91Lm...
GARMIN_POLL_INTERVAL=15
GARMIN_WATCH_STALE_AFTER=600
GARMIN_ENTITY_BLOCKLIST=camera.front_door,media_player.tv
GARMIN_LOG_LEVEL=INFO
```

### The exposure lists

The allow list and the block list of the bridge are the last word.  The
integration also has its own exposure options, and the two are combined:

* the bridge only ever exposes an entity when it passes its own allow and
  block lists,
* the integration can narrow the list further with its *exposed entities*
  option.

An empty *exposed entities* list in the integration means *do not narrow the
list*.  A non-empty list means *only these entities*, and the bridge lists
are applied on top of it.

## The Home Assistant integration

### The setup step

| Field | Description |
| --- | --- |
| Bridge URL | The address the integration uses to reach the bridge, for example `http://garmin-bridge:8099`.  The default is `http://garmin-bridge:8099`. |
| Bridge token | The value of `GARMIN_BRIDGE_TOKEN`. |

The integration verifies the bridge with `GET /v1/health` before it accepts
the entry.  A bridge that cannot be reached produces *Could not reach the
bridge*.

### The options

Open *Settings* → *Devices & services* → *Garmin Home Assistant* →
*Configure*.

| Option | Default | Description |
| --- | --- | --- |
| Exposed entities | empty | The entities the watches may see and control.  An empty list exposes every controllable entity. |
| Blocked entities | empty | Entities that are never shown on the watch, even when they are in the exposed list. |
| Phone notification service | empty | The notify service the messages are mirrored to, for example `mobile_app_iphone`.  The Garmin Connect app then pushes them to the watch. |
| Create mirror switches | off | Create a switch in Home Assistant for every entity the watch can toggle. |
| Update interval | `30` | Seconds between two polls of the bridge by the integration.  The minimum is 5 seconds. |

Changing an option reloads the integration.

### The entities

The integration creates the following entities for every paired watch:

| Entity | Type | Description |
| --- | --- | --- |
| `<watch> Connected` | Binary sensor | On while the watch has talked to the bridge recently. |
| `<watch> Battery` | Sensor | The battery level the watch reported. |
| `<watch> Steps` | Sensor | The step count the watch reported. |
| `<watch> Heart rate` | Sensor | The heart rate the watch reported. |
| `<watch> Last seen` | Sensor | When the watch was last seen. |
| `<watch> Test notification` | Button | Sends a test notification to this watch. |

With *Create mirror switches* enabled there is one extra switch per
controllable entity, named `Garmin <entity name>`.

## The watch application

The settings live in `resources/settings/properties.xml` and are edited in the
Garmin Connect IQ app or in Garmin Express.

| Setting | Default | Description |
| --- | --- | --- |
| Bridge URL | `http://homeassistant.local:8099` | The address of the bridge.  Use an address the watch can resolve, for example the IP address of the machine that runs the bridge. |
| Bridge token | empty | The value of `GARMIN_WATCH_TOKEN`.  Only needed for the first start, after that the watch uses the token the bridge issued for it. |
| Poll interval | `30` | Seconds between two polls while the application is in the foreground.  `0` asks the bridge for its own interval.  The shortest useful value is 10 seconds. |
| Group entities by area | on | Whether the entity list is grouped by the Home Assistant area. |
| Confirm commands | off | Whether a command has to be confirmed before it runs. |

The watch also keeps its own state, which is not visible in the settings:

| Value | Description |
| --- | --- |
| Watch id | The id the bridge knows the watch by.  It is generated on the first start. |
| Device token | The token the bridge issued for this watch. |
| Revision | The revision of the entity list the watch already knows. |
| Notification cursor | The last notification the watch saw. |
| Background interval | The interval of the background service, at least 300 seconds. |

## Home Assistant automations

The integration fires an event when a watch acknowledges a notification with
an action:

```yaml
automation:
  - alias: "Garmin - front door"
    triggers:
      - trigger: event
        event_type: garmin_homeassistant_watch_action
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.action == 'open' }}"
    actions:
      - action: lock.open
        target:
          entity_id: lock.front_door
```

The data of the event contains the `watch_id`, the `action` and the
`entity_id` the notification was about.

## Which entities can be controlled

The bridge exposes the domains that make sense on a watch:

`alarm_control_panel`, `binary_sensor`, `climate`, `cover`, `fan`,
`humidifier`, `input_boolean`, `light`, `lock`, `media_player`, `remote`,
`scene`, `script`, `switch` and `vacuum`.

Entities of other domains, such as `sensor`, are not exposed.  See
[`entities.md`](entities.md) for the commands of every domain.
