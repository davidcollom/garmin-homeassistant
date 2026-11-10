# Garmin Home Assistant

Control your Home Assistant from a Garmin watch, and let Home Assistant talk
back.

[![CI](https://github.com/davidcollom/garmin-homeassistant/actions/workflows/ci.yml/badge.svg)](https://github.com/davidcollom/garmin-homeassistant/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Garmin Home Assistant is an open source bridge between [Home Assistant] and
Garmin watches that run [Connect IQ].  It is made of three parts:

| Part | Where | What it does |
| --- | --- | --- |
| Watch app | [`watch/`](watch) | A Connect IQ application for the Garmin Venu 4 and the Edge 1040 / Edge 1040 Solar. |
| Bridge | [`bridge/`](bridge) | A small service that proxies the Home Assistant REST API and holds the access token. |
| Home Assistant integration | [`custom_components/garmin_homeassistant/`](custom_components/garmin_homeassistant) | The entities, the services and the `notify` platform. |

**No Garmin cloud account and no Garmin Connect IQ API are needed for the
core function.**  The watch talks to the bridge over HTTP, the bridge talks
to Home Assistant over its own REST API.  The Garmin cloud is only involved
if you choose to mirror a notification to the phone, because the Garmin
Connect app on the phone is what pushes it to the wrist.

## Features

* **Entity control from the wrist** – lights, switches, locks, covers,
  climate, fans, media players, vacuums, alarm panels, scenes and scripts.
* **Notifications to the watch** – a queue in the bridge, an inbox in the app
  and optional action buttons.
* **Entity state on the watch** – the states are mirrored by the bridge, so
  the watch always has an answer.
* **Customisation** – choose which entities the watches may see, group them
  by Home Assistant area, pin the important ones, ask for a confirmation
  before a command runs, tune the poll interval and pick the notification
  priority.
* **Small** – the watch application is written in Monkey C, keeps no
  background service alive on the Edge 1040 and uses a compact wire format.

## Supported devices

| Device | Connect IQ | Notification presenter | Notes |
| --- | --- | --- | --- |
| Garmin Venu 4 | 6.0 | `Toybox.Notifications` with action buttons | Full feature set. |
| Garmin Edge 1040 / Edge 1040 Solar | 6.0 | Toast plus the in-app inbox | The Edge 1040 does not implement `Toybox.Notifications`. |

The two watches do not implement the same set of Connect IQ modules.  The
application detects what the device can do at runtime and adapts.  The
detailed list is in [`docs/ciq-device-capabilities.md`](docs/ciq-device-capabilities.md),
and the summary is in [`docs/device-support.md`](docs/device-support.md).

> Garmin sells the solar variant of the Edge 1040 as the *Edge 1040 Solar*.
> There is no *Forerunner 1040 Solar*, and the Connect IQ compatible device
> list has no Forerunner 1040 at all, so the Edge 1040 is the only device of
> that family this project supports.

## Architecture

```text
   ┌────────────────────┐        HTTP/JSON        ┌────────────────────┐
   │  Garmin watch      │ ──────────────────────► │  Bridge            │
   │  Connect IQ app    │ ◄────────────────────── │  (FastAPI)         │
   └────────────────────┘                         └─────────┬──────────┘
                                                          │ REST + websocket
                                                          ▼
                                                ┌────────────────────┐
                                                │  Home Assistant    │
                                                └────────────────────┘
```

1. The watch registers itself with the bridge and receives a token of its
   own.
2. The watch polls `GET /v1/entities` and receives a compact snapshot of the
   entities it may control.
3. The user taps an entity, the watch posts a command to `/v1/commands` and
   the bridge turns it into a Home Assistant service call.
4. Home Assistant queues a notification, the integration posts it to
   `/v1/admin/notify` and the watch picks it up on its next poll.

More details are in [`docs/architecture.md`](docs/architecture.md).

## Installation

The full guide is in [`docs/installation.md`](docs/installation.md).  In short:

1. Run the bridge:

   ```bash
   docker compose up -d
   ```

2. Install the Home Assistant integration through [HACS] or by copying
   `custom_components/garmin_homeassistant` into the `custom_components`
   folder of your Home Assistant configuration.  Add the integration and
   enter the URL and the `GARMIN_BRIDGE_TOKEN` of the bridge.

3. Build the watch application with the [Connect IQ SDK] and install it on
   the watch.  Set the bridge URL and the `GARMIN_WATCH_TOKEN` in the
   settings of the application.

## Documentation

| Page | Content |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | The three parts, the data flow and the wire format. |
| [`docs/installation.md`](docs/installation.md) | Installing the bridge, the integration and the watch app. |
| [`docs/configuration.md`](docs/configuration.md) | Every setting of the bridge, the integration and the watch app. |
| [`docs/entities.md`](docs/entities.md) | Which entities can be controlled and how. |
| [`docs/notifications.md`](docs/notifications.md) | Notifications to the watch and the phone mirroring. |
| [`docs/customisation.md`](docs/customisation.md) | The customisation options. |
| [`docs/device-support.md`](docs/device-support.md) | What the Venu 4 and the 1040 Solar can and cannot do. |
| [`docs/ciq-device-capabilities.md`](docs/ciq-device-capabilities.md) | The full Connect IQ capability matrix of the two devices. |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | What to do when something does not work. |
| [`docs/development.md`](docs/development.md) | Working on the repository. |

## Development

```bash
make install      # install the development tools
make test         # run every test suite
make lint         # run ruff and mypy
make watch-check  # run the static checks of the Connect IQ sources
```

The Connect IQ SDK is proprietary and cannot be redistributed, so the watch
application is **not compiled** by the open source CI pipeline.  Instead the
pipeline runs a static check of the Monkey C sources, the XML resources and
the manifest.  This is a real limitation and it is documented as such in
[`docs/development.md`](docs/development.md).

## Licence

MIT, see [LICENSE](LICENSE).  This project is not affiliated with Garmin or
with Home Assistant.

[Home Assistant]: https://www.home-assistant.io
[Connect IQ]: https://developer.garmin.com/connect-iq/
[Connect IQ SDK]: https://developer.garmin.com/connect-iq/download/
[HACS]: https://hacs.xyz
