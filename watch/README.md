# Garmin Home Assistant — Connect IQ watch app

This directory holds the Connect IQ application that runs on the watch.  It
talks to the [bridge](../bridge) over plain HTTP and lets you control your
Home Assistant entities and read the notifications that Home Assistant sends
to the watch.

## Requirements

* The [Connect IQ SDK](https://developer.garmin.com/connect-iq/download/).
  It is proprietary and cannot be redistributed, which is why the
  application is not compiled in the open source CI pipeline.
* A Garmin developer key for the debug (sideload) builds.  The release
  builds are signed by Garmin when the application is submitted.

## Building

```bash
export MONKEYC="$HOME/connectiq/bin/monkeyc"
export GARMIN_DEVELOPER_KEY="$HOME/.garmin/developer_key"

./build.sh venu     # Venu 4
./build.sh edge     # Edge 1040 and Edge 1040 Solar
./build.sh both     # both variants
./build.sh all      # both variants and a fresh launcher icon
```

The result is a `.prg` file in `watch/build/`.  Copy it to the watch and
install it with the [Garmin Connect IQ app](https://apps.garmin.com) or
sideload it with the `monkeyc` command from the SDK.

## Layout

| Path | Content |
| --- | --- |
| `manifest.xml` | Manifest of the Venu 4 build. |
| `manifest-edge.xml` | Manifest of the Edge 1040 build. |
| `monkey.jungle` | Jungle file of the Venu 4 build. |
| `monkey-edge.jungle` | Jungle file of the Edge 1040 build. |
| `source/` | The shared Monkey C sources. |
| `variants/notifications/` | Presenter for devices with `Toybox.Notifications`. |
| `variants/toast/` | Presenter for devices without `Toybox.Notifications`. |
| `resources/` | Strings, properties, settings and the launcher icon. |
| `tools/` | Helper scripts, for example the launcher icon generator. |
| `build.sh` | Build script for the two variants. |

## Why there are two builds

The Venu 4 implements `Toybox.Notifications`, which lets the application
raise a system notification with buttons.  The Edge 1040 does not, so the
Edge build asks the user to open the app instead and shows the
notification in the inbox of the application.  Everything else is shared,
which is why the sources live in `source/` and only the presenter differs.

See [`docs/ciq-device-capabilities.md`](../docs/ciq-device-capabilities.md)
for the full list of the modules that the two devices implement.

## Static checks

The CI pipeline cannot compile the application, so it runs a static check
instead:

```bash
python3 scripts/check_ciq.py
```

The script verifies the XML resources, the references between the sources
and the resources, the brackets of every file and a list of API calls that
either do not exist or are not available on the Edge 1040.

## Limits

* The application polls the bridge while it is in the foreground.  The
  background service only refreshes the notification queue, because the
  Edge 1040 only offers 32 KB of memory for a background service.
* The watch needs to reach the bridge, so the bridge has to be reachable
  from the network of the phone.  A self signed certificate is not
  supported by the Connect IQ runtime, so use a certificate from a public
  authority or plain HTTP on a trusted network.
