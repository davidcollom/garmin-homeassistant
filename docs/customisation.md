# Customisation

There are a lot of small knobs, on three different levels: the bridge
decides what is possible, the Home Assistant integration decides what is
allowed and the watch application decides how it looks.

## What the watches may see

This is the most important customisation, because it decides what the
watch can do at all.

### In Home Assistant

*Settings* → *Devices & services* → *Garmin Home Assistant* → *Configure*.

| Option | Effect |
| --- | --- |
| Exposed entities | Only these entities appear on the watch.  An empty list exposes every controllable entity. |
| Blocked entities | These entities never appear, even when they are in the exposed list. |

The entity picker only offers the domains that the watch can control, so
there is no way to expose something the watch cannot do anything with.

### In the bridge

| Variable | Effect |
| --- | --- |
| `GARMIN_ENTITY_ALLOWLIST` | The outer limit.  An entity that is not on this list is never exposed, whatever the integration says.  An empty list means no limit. |
| `GARMIN_ENTITY_BLOCKLIST` | The entities that are never exposed.  This list is not overwritten by the integration. |

The two lists are combined:

* an entity has to pass the allow list of the bridge,
* and it has to be in the selection of the integration, unless that
  selection is empty,
* and it must not be on any block list.

### On the watch

The watch does not have its own allow list; it shows what the bridge sends.

## How the entity list looks

### Grouping by area

The *Group entities by area* setting of the watch application groups the
list by the Home Assistant area of the entity.  The areas come from the
Home Assistant area registry, so the grouping is the same as in the Home
Assistant interface.

Turn the setting off to get one flat list.

### The order of the list

The bridge sends the entities in the order Home Assistant knows them.  The
watch keeps that order, and the first screen shows the entities of the first
area.

There is a `PINNED` flag in the compact format for entities that should be
at the top of the list.  The bridge does not set it yet, but a custom
integration or a future version can.

### The page size

The watch asks for the entities in pages so that a big Home Assistant
instance does not send everything at once.  The page size is part of the
configuration the watch reads from `GET /v1/config`.

## How the commands behave

### Asking for a confirmation

The *Confirm commands* setting of the watch application makes every command
ask for a confirmation before it runs.  It is useful when the watch is used
by more than one person or when a command has consequences that are not
obvious, such as unlocking a door.

### The poll interval

The *Poll interval* setting of the watch application is the number of
seconds between two polls while the application is in the foreground.  A
value of `0` asks the bridge for its own interval.

| Value | Effect |
| --- | --- |
| 10 | The freshest states, the most traffic. |
| 30 | A good default. |
| 60 or more | Fewer requests, a staler list. |

The bridge uses `GARMIN_POLL_INTERVAL` for the same purpose on its side, and
the watch reads it from `GET /v1/config`.

## How the notifications behave

### The priority

Every notification has a priority: `low`, `normal` or `high`.  A high
priority notification is shown with an accent colour on the devices that
support it.

```yaml
action: garmin_homeassistant.send_notification
data:
  message: Somebody is at the front door.
  title: Doorbell
  priority: high
```

### The actions

The buttons underneath a message are entirely up to the automation:

```yaml
action: garmin_homeassistant.send_notification
data:
  message: The heating is off.
  title: Climate
  entity_id: climate.living_room
  actions:
    - id: heat
      label: Heat
    - id: ignore
      label: Ignore
```

The id of the chosen action comes back in the
`garmin_homeassistant_watch_action` event, so an automation can react to it.

### Which watches get the message

The `watch_ids` field of the service limits the message to specific
watches:

```yaml
action: garmin_homeassistant.send_notification
data:
  message: Only for the Venu.
  watch_ids:
    - venu441mm-1a2b3c
```

Without it, every watch gets the message.

### The phone

The *Phone notification service* option mirrors every message to a notify
service, so the Garmin Connect app pushes it to the wrist.  This is the
option that makes the delivery fast when the watch application is closed.

## The Home Assistant side

### The mirror switches

With *Create mirror switches* enabled, the integration creates a switch for
every entity the watch can toggle.  The switches are named `Garmin <name>`
and they send the same commands the watch sends, which makes them handy for
dashboards and for automations that want to know what the watch is allowed
to see.

### The watch entities

Every paired watch gets its own device in Home Assistant with a set of
entities:

| Entity | Type |
| --- | --- |
| Connected | Binary sensor |
| Battery | Sensor |
| Steps | Sensor |
| Heart rate | Sensor |
| Last seen | Sensor |
| Test notification | Button |

The *Test notification* button sends a message to that watch, which is the
quickest way to check that the whole chain works.

### The update interval

The *Update interval* option of the integration controls how often Home
Assistant asks the bridge for the state of the watches and the entities.
The minimum is 5 seconds, the default is 30 seconds.

This is independent of the interval the watch uses: the watch talks to the
bridge directly and does not go through Home Assistant.

### The services

| Service | Purpose |
| --- | --- |
| `garmin_homeassistant.send_notification` | Queue a notification. |
| `garmin_homeassistant.run_command` | Run a command through the bridge. |
| `garmin_homeassistant.set_exposed_entities` | Change the exposed entities. |
| `garmin_homeassistant.refresh` | Ask the bridge to re-read the Home Assistant states. |

`set_exposed_entities` changes the exposure list and stores it in the
options of the integration, so it survives a restart:

```yaml
action: garmin_homeassistant.set_exposed_entities
data:
  entity_ids:
    - light.kitchen
    - lock.front_door
```

## A complete example

A setup where only the hallway light and the front door are exposed, the
notifications go to the phone as well and every command has to be confirmed:

```yaml
# The bridge
#   GARMIN_ENTITY_ALLOWLIST=light.hallway,lock.front_door
#   GARMIN_WATCH_STALE_AFTER=600

# The Home Assistant options of the integration
#   exposed_entities: [light.hallway, lock.front_door]
#   blocked_entities: []
#   phone_notify_service: mobile_app_iphone
#   create_mirror_switches: true
#   scan_interval: 30

# The watch application
#   BridgeUrl: http://192.168.1.10:8099
#   PollInterval: 30
#   ShowAreas: true
#   ConfirmCommands: true
```
