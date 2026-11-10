# Notifications to the watch

Home Assistant can send a message to the watch.  There are two ways and they
can be used together.

## The notify platform

The integration registers a normal notification service:

```yaml
action: notify.garmin_homeassistant
data:
  message: The washing machine has finished.
  title: Laundry
```

The message is queued in the bridge and delivered the next time the watch
polls.  The `notify` platform supports the usual fields:

| Field | Description |
| --- | --- |
| `message` | The body of the notification.  Required. |
| `title` | The headline.  Defaults to *Home Assistant*. |
| `data` | A dictionary with the extra fields below. |

The extra fields go into `data`:

```yaml
action: notify.garmin_homeassistant
data:
  message: The front door is open.
  title: Doorbell
  data:
    priority: high
    entity_id: binary_sensor.front_door
    actions:
      - id: open
        label: Open
```

| Field | Description |
| --- | --- |
| `priority` | `low`, `normal` or `high`.  A high priority notification is shown with an accent colour. |
| `entity_id` | The entity the notification is about.  The watch offers it as a shortcut. |
| `actions` | The buttons underneath the message.  Every action is a dictionary with an `id` and a `label`. |

## The dedicated service

The integration also offers a service that does the same thing but with the
extra fields as first class arguments:

```yaml
action: garmin_homeassistant.send_notification
data:
  message: The washing machine has finished.
  title: Laundry
  priority: high
  entity_id: switch.washing_machine
  watch_ids:
    - edge1040-1a2b3c
  actions:
    - id: ack
      label: Acknowledge
```

| Field | Description |
| --- | --- |
| `message` | The body of the notification.  Required. |
| `title` | The headline.  Defaults to *Home Assistant*. |
| `priority` | `low`, `normal` or `high`. |
| `entity_id` | The entity the notification is about. |
| `watch_ids` | Limit the notification to these watches.  Empty means every watch. |
| `actions` | The buttons underneath the message. |

The difference to the notify platform is the `watch_ids` field and the fact
that the service answers nothing, while `notify.garmin_homeassistant` is
usable by every automation that speaks the notify protocol.

## How a notification reaches the watch

1. Home Assistant calls the service.
2. The integration posts the notification to `POST /v1/admin/notify` on the
   bridge.
3. The bridge puts it in the queue of every watch that is addressed.
4. The watch polls `GET /v1/notifications` and receives the notifications it
   has not acknowledged yet.
5. The watch shows them in its inbox and, on a device that supports it,
   raises a system notification.
6. The watch acknowledges the notification with
   `POST /v1/notifications/<id>/ack`, optionally with the action the user
   picked.

Every watch has its own cursor, so a notification that one watch has
acknowledged is still waiting for the other one.  The queue of a watch holds
a bounded number of notifications; the oldest ones are dropped when it
overflows.

## The actions

An action is a pair of an id and a label.  The id travels back to Home
Assistant, the label is what the user sees on the watch.

```yaml
actions:
  - id: open
    label: Open
  - id: ignore
    label: Ignore
```

When the user picks an action, the watch acknowledges the notification with
that action and the bridge fires a Home Assistant event:

```yaml
automation:
  - alias: "Garmin - open the door"
    triggers:
      - trigger: event
        event_type: garmin_homeassistant_watch_action
    actions:
      - action: lock.open
        target:
          entity_id: lock.front_door
```

The event carries:

| Field | Description |
| --- | --- |
| `watch_id` | The watch that picked the action. |
| `action` | The id of the action. |
| `entity_id` | The entity the notification was about, when there was one. |
| `notification_id` | The id of the notification. |

## The difference between the two watches

The Venu 4 implements `Toybox.Notifications`, so the application can raise a
system notification with buttons.  The user picks a button without opening
the application.

The Edge 1040 / Edge 1040 Solar does not implement the module, so the
application shows a toast and asks the user to open the application.  The
notification is then in the inbox, where the same actions are offered.

The difference is in the presentation only: the queue, the actions and the
events are the same on both devices.  See
[`device-support.md`](device-support.md).

## Mirroring to the phone

The watch only polls the bridge while the application is in the foreground.
When the application is closed, a notification waits until the user opens it.

The Garmin Connect app on the phone mirrors phone notifications to the
watch.  To use that, configure a phone notification service in the options of
the integration:

```text
mobile_app_iphone
```

The integration then sends every message to that service as well, and the
Garmin Connect app pushes it to the wrist.  The message is delivered twice
when the watch app is open, once through the bridge and once through the
phone.

The mirroring is best effort: if the phone service fails, the notification
still reaches the watch through the bridge.

## Automations

A typical doorbell automation looks like this:

```yaml
automation:
  - alias: "Doorbell"
    triggers:
      - trigger: state
        entity_id: binary_sensor.front_door
        to: "on"
    actions:
      - action: notify.garmin_homeassistant
        data:
          message: Somebody is at the front door.
          title: Doorbell
          data:
            priority: high
            entity_id: binary_sensor.front_door
            actions:
              - id: open
                label: Open
```

## Limitations

* The body of a notification is truncated to a length that fits on the
  screen of the watch.  Put the important part at the beginning.
* A notification is only raised once per watch.  The inbox keeps the
  notifications until they are acknowledged, so nothing is lost when the user
  ignores the toast.
* The mirror to the phone needs the Garmin Connect app, the Garmin cloud
  and a phone that is online.  The core function of this project does not
  need any of them.
