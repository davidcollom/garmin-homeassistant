# Controlling entities from the watch

The watch shows the entities the bridge exposes, grouped by the Home Assistant
area.  Tap an entity to see its state and the actions it supports.

## Which entities are exposed

The bridge only exposes the domains that make sense on a watch:

| Domain | What the watch can do |
| --- | --- |
| `light` | On, off, toggle, brightness. |
| `switch` | On, off, toggle. |
| `input_boolean` | On, off, toggle. |
| `fan` | On, off, toggle, speed. |
| `humidifier` | On, off, toggle, humidity. |
| `lock` | Lock, unlock. |
| `cover` | Open, close, stop, position. |
| `climate` | On, off, heat, cool, temperature. |
| `alarm_control_panel` | Arm away, arm home, disarm. |
| `media_player` | Play, pause, next, previous. |
| `remote` | On, off, toggle. |
| `scene` | Activate. |
| `script` | Run. |
| `vacuum` | Start, pause, return to base. |
| `binary_sensor` | Read only. |

Everything else, including the plain `sensor` domain, stays in Home Assistant.
A watch screen is not a good place for a graph.

## The commands

A command is a short word plus the entity it applies to.  The bridge turns
it into the Home Assistant service that fits the domain.

| Command | Effect |
| --- | --- |
| `toggle` | Switch the entity, taking its current state into account. |
| `turn_on` | Switch the entity on. |
| `turn_off` | Switch the entity off. |
| `open` | Open a cover, unlock a lock, arm an alarm. |
| `close` | Close a cover, lock a lock, disarm an alarm. |
| `set_level` | Set a numeric value, for example a brightness or a temperature. |
| `set_value` | The same as `set_level`. |
| `service` | Call any Home Assistant service. |

### What `toggle` does per domain

`toggle` is not always "call the opposite service".  The bridge looks at the
state first:

| Domain | Behaviour |
| --- | --- |
| `lock` | Unlock a locked lock, lock an unlocked one. |
| `cover` | Open a closed cover, close an open one. |
| `alarm_control_panel` | Disarm an armed panel, arm it when it is disarmed. |
| `vacuum` | Pause a cleaning vacuum, start an idle one. |
| `media_player` | Pause a playing player, start a stopped one. |
| everything else | Call the *on* service when the state is not one of the active states, the *off* service otherwise. |

The active states are `on`, `open`, `open_cover`, `playing`, `home`,
`armed_away`, `armed_home`, `armed_night`, `armed_vacation`,
`armed_custom_bypass`, `locked`, `active`, `heat`, `cool` and `auto`.

### The domain specific services

| Domain | `turn_on` | `turn_off` | Extra commands |
| --- | --- | --- | --- |
| `alarm_control_panel` | `alarm_arm_away` | `alarm_disarm` | `arm_home`, `arm_away`, `disarm` |
| `climate` | `turn_on` | `turn_off` | `heat`, `cool`, `off` |
| `cover` | `open_cover` | `close_cover` | `stop` |
| `fan` | `turn_on` | `turn_off` | – |
| `humidifier` | `turn_on` | `turn_off` | – |
| `input_boolean` | `turn_on` | `turn_off` | – |
| `light` | `turn_on` | `turn_off` | – |
| `lock` | `unlock` | `lock` | `unlock`, `lock` |
| `media_player` | `media_play` | `media_pause` | `play`, `pause`, `next`, `previous` |
| `remote` | `turn_on` | `turn_off` | – |
| `scene` | `turn_on` | `turn_off` | – |
| `script` | `turn_on` | `turn_off` | – |
| `switch` | `turn_on` | `turn_off` | – |
| `vacuum` | `start` | `return_to_base` | `start`, `pause`, `dock` |

### Numeric values

`set_level` takes the value in `data`:

```json
{"cmd": "set_level", "entity_id": "light.kitchen", "data": {"value": 40}}
```

The bridge maps the value onto the attribute that fits the domain:

| Domain | Service | Payload |
| --- | --- | --- |
| `light` | `turn_on` | `brightness_pct` |
| `climate` | `set_temperature` | `temperature` |
| `cover` | `set_cover_position` | `position` |
| everything else | `turn_on` | `percentage` |

### Calling an arbitrary service

The `service` command calls any service, as long as the Home Assistant token
is allowed to call it:

```json
{
  "cmd": "service",
  "entity_id": "light.kitchen",
  "service": "light.turn_on",
  "data": {"brightness_pct": 60}
}
```

The service name may be given with or without a domain.  Without a domain the
domain of the entity is used.

## The answer of the bridge

Every command answers with a short result that fits on a watch screen:

```json
{"ok": true, "message": "light.turn_on", "state": "on"}
```

| Field | Meaning |
| --- | --- |
| `ok` | Whether the command reached Home Assistant. |
| `message` | The service that was called, or a short error. |
| `state` | The state of the entity after the command, when it is known. |

## Trying the commands from Home Assistant

The integration offers the same mechanism as a service, which makes it easy
to test an automation without touching the watch:

```yaml
action: garmin_homeassistant.run_command
data:
  command: toggle
  entity_id: light.kitchen
response_variable: result
```

The service answers with the same object as the bridge.

## Limitations

* The bridge uses the plain Home Assistant REST API.  There is no fine
  grained permission model, so the token of the bridge can call every
  service.  Run the bridge in a network you trust, or use a dedicated
  Home Assistant instance.
* Only the services listed above are reachable through the short commands.
  Everything else needs the `service` command, which is not offered on the
  watch screen.
* The state on the watch is the state the bridge saw.  It is updated through
  the Home Assistant websocket, so it is normally less than a second old,
  but it is a copy and not a live subscription.
* An entity that is not controllable, for example a `binary_sensor`, is
  shown but cannot be switched.
