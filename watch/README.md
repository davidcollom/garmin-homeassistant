# Garmin Home Assistant — Connect IQ watch app

This directory holds the Connect IQ application that runs on the watch.  It
talks to the [bridge](../bridge) over plain HTTP and lets you control your
Home Assistant entities and read the notifications that Home Assistant sends
to the watch.

## Where the application comes from

The application is published in two ways.

* **The releases of this repository** carry the signed `.iq` files as
  attachments.  People download the file for their watch and copy it into
  the `GARMIN/APPS` folder of the watch over USB.  This works for everybody
  and needs no Garmin account.  The instructions are in
  [`docs/installation.md`](../docs/installation.md).
* **The Garmin Connect IQ store** carries the application as well.  People
  install it with the Garmin Connect app on their phone, which pushes it to
  the watch over Bluetooth.  Publishing in the store needs an account of
  the Garmin Connect IQ developer program and a review by Garmin.

Both are built from the same sources.

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

The result is a `.iq` file in `watch/build/`.  Copy it to the watch and
install it with the [Garmin Connect IQ app](https://apps.garmin.com) or
sideload it with the `monkeyc` command from the SDK.

A second argument selects the kind of build:

```bash
./build.sh both release
```

A release build is an unsigned `.prg` file.  It is what is submitted to the
Connect IQ store, which signs it.

## Publishing

### The release of this repository

The `.github/workflows/watch-build.yml` workflow builds the application and
attaches the files to the release of a tag.

The workflow cannot run on a GitHub hosted runner, because the Connect IQ
SDK cannot be downloaded there.  It runs on a **self hosted runner** with
the SDK installed instead:

1. Install the [Connect IQ SDK](https://developer.garmin.com/connect-iq/download/)
   on a machine that is always on.
2. Register it as a GitHub Actions runner with the label `connectiq`:

   ```bash
   ./config.sh --url https://github.com/davidcollom/garmin-homeassistant \
       --token <the runner token of the repository> --labels connectiq
   ./run.sh
   ```

3. Add the secrets of the repository:

   | Secret | Content |
   | --- | --- |
   | `GARMIN_DEVELOPER_KEY` | The developer key, base64 encoded. |
   | `GARMIN_STORE_API_KEY` | The API key of the Connect IQ developer program.  Only needed for the store. |
   | `GARMIN_STORE_DISTRIBUTION_KEY` | The distribution key, base64 encoded.  Only needed for the store. |

   The base64 encoding is made with `base64 -w0 developer_key`.

4. Add the variable of the repository, if the `monkeyc` binary is not on the
   path of the runner:

   | Variable | Content |
   | --- | --- |
   | `MONKEYC` | The path of the `monkeyc` binary, for example `/opt/connectiq/bin/monkeyc`. |

5. Tag a release:

   ```bash
   git tag v0.1.0 && git push origin v0.1.0
   ```

The workflow then builds both variants, attaches `venu.iq` and `edge.iq` to
the release and, when the store keys are present, submits the release
builds to the Connect IQ store.

### The Connect IQ store

The store needs an account of the Garmin Connect IQ developer program.  With
that account the application id of the manifest is registered, and the
`.prg` files are uploaded with the SDK:

```bash
monkeyc publish -o watch/build/venu.prg \
    --api-key "$GARMIN_STORE_API_KEY" \
    --key "$HOME/.garmin/distribution_key"
```

Garmin reviews the submission and publishes the application in the store.
The beta channel of the store is an alternative: publish a beta build and
people can opt in from the Garmin Connect app.

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
