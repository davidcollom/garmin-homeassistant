# Installation

There are three things to install: the bridge, the Home Assistant integration
and the watch application.  They can be installed in any order, but the
bridge has to be running before the watch can register itself.

## 1. The bridge

The bridge needs to be reachable from the watch, which means from the local
network of the phone.  It does **not** need to be reachable from the
internet.

### With Docker Compose

The repository has a `docker-compose.yml` that is ready to use:

```bash
git clone https://github.com/davidcollom/garmin-homeassistant.git
cd garmin-homeassistant
cp docker-compose.yml my-compose.yml
```

Edit `my-compose.yml` and fill in at least:

```yaml
environment:
  HA_URL: "http://homeassistant:8123"
  HA_TOKEN: "<the long lived access token of Home Assistant>"
  GARMIN_BRIDGE_TOKEN: "<a long random string>"
  GARMIN_WATCH_TOKEN: "<another long random string>"
```

Then start it:

```bash
docker compose -f my-compose.yml up -d
```

### With Docker directly

```bash
docker build -t garmin-homeassistant-bridge:latest .
docker run -d --name garmin-bridge \
    --restart unless-stopped \
    -p 8099:8099 \
    -e HA_URL=http://homeassistant:8123 \
    -e HA_TOKEN=... \
    -e GARMIN_BRIDGE_TOKEN=... \
    -e GARMIN_WATCH_TOKEN=... \
    garmin-homeassistant-bridge:latest
```

### From the sources

Python 3.11 or newer is required.

```bash
git clone https://github.com/davidcollom/garmin-homeassistant.git
cd garmin-homeassistant/bridge
python -m venv .venv
. .venv/bin/activate
pip install -e .
export HA_URL=http://homeassistant:8123
export HA_TOKEN=...
export GARMIN_BRIDGE_TOKEN=...
export GARMIN_WATCH_TOKEN=...
garmin-bridge
```

### The tokens

Generate the two tokens with a password manager or with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

* `GARMIN_BRIDGE_TOKEN` is used by the Home Assistant integration.
* `GARMIN_WATCH_TOKEN` is used by the watch app.  It is a bootstrap token:
  the bridge hands the watch a token of its own on the first registration.

Keep them out of version control.  Do not reuse the Home Assistant access
token as a bridge token.

### The Home Assistant access token

Create a long-lived access token in Home Assistant under your profile:

* click on your user name in the sidebar,
* open the security tab,
* scroll down to *Long-lived access tokens*,
* create a token called `garmin-bridge` and copy it.

The token needs the full API access, because the bridge reads the states and
calls the services.  If you use the fine-grained mode of Home Assistant, allow
`read` on the states and the area registry, and `execute` on the services of
the domains you want to control.

### Checking that the bridge works

```bash
curl http://localhost:8099/v1/health
```

```json
{"ok": true, "version": "0.1.0"}
```

The health route needs no token.  If the bridge complains about the
configuration, it prints the problems on the standard error, for example
`HA_TOKEN is required (Home Assistant long-lived access token)`.

## 2. The Home Assistant integration

The integration needs Home Assistant 2024.11 or newer.

### With HACS

1. Add this repository to HACS as a custom repository of the category
   *Integration*.
2. Install *Garmin Home Assistant*.
3. Restart Home Assistant.

### Manually

Copy the folder into the configuration directory of Home Assistant:

```bash
cp -r custom_components/garmin_homeassistant \
    /path/to/homeassistant/config/custom_components/
```

and restart Home Assistant.

### Adding the integration

1. Go to *Settings* → *Devices & services*.
2. Press *Add integration* and search for *Garmin Home Assistant*.
3. Fill in the form:

   | Field | Value |
   | --- | --- |
   | Bridge URL | The address the watch and Home Assistant use to reach the bridge, for example `http://garmin-bridge:8099` or `https://garmin-bridge.example.com`. |
   | Bridge token | The value of `GARMIN_BRIDGE_TOKEN`. |

4. Press *Submit*.

The integration checks the bridge with a `GET /v1/health` before it accepts
the entry.  If the bridge cannot be reached or the token is wrong, the form
shows *Could not reach the bridge*.

The options of the integration are described in
[`configuration.md`](configuration.md).

## 3. The watch application

The watch application is a Connect IQ program.  Building it needs the
[Connect IQ SDK], which is proprietary and has to be downloaded from Garmin.

### Building

```bash
cd watch
export MONKEYC="$HOME/connectiq/bin/monkeyc"
export GARMIN_DEVELOPER_KEY="$HOME/.garmin/developer_key"
./build.sh venu    # the Venu 4
./build.sh edge    # the Edge 1040 and the Edge 1040 Solar
./build.sh both    # both
```

The result is a `.prg` file in `watch/build/`.

### Sideloading a debug build

A debug build is signed with your developer key and can be installed
directly:

```bash
monkeyc -f watch/monkey.jungle -d -k "$GARMIN_DEVELOPER_KEY" \
    -o watch/build/venu.prg
```

Connect the watch over USB and run:

```bash
garmin-install watch/build/venu.prg
```

The `garmin-install` tool is part of the SDK.

### Installing a release build

Upload the `.prg` file to the [Garmin Connect IQ store] and install it from
the Garmin Connect IQ app on your phone, or from Garmin Express on the
desktop.  The store page needs the application id from the manifest.

### Configuring the application

Open the settings of the application:

* on the phone: *Garmin Connect* → *My Apps* → *Garmin Home Assistant* →
  *App Settings*,
* on the desktop: Garmin Express → *Apps* → *Garmin Home Assistant* →
  *Settings*.

Fill in:

| Setting | Value |
| --- | --- |
| Bridge URL | The address of the bridge, for example `http://192.168.1.10:8099`. |
| Bridge token | The value of `GARMIN_WATCH_TOKEN`. |
| Poll interval | Seconds between two polls.  `0` asks the bridge for its own interval. |
| Group entities by area | Whether the entity list is grouped by Home Assistant area. |
| Confirm commands | Whether a command has to be confirmed before it runs. |

The first start of the application registers the watch with the bridge.  The
bridge then issues a token for this watch and stores it on the watch, so the
shared `GARMIN_WATCH_TOKEN` is only needed for the first start.

### The network

The watch can only reach the bridge over a network it can reach.  A few
things to keep in mind:

* The watch needs an internet connection for its own services, but the
  bridge may live on the local network only.
* A self signed certificate is not accepted by the Connect IQ runtime.  Use
  a certificate from a public authority or plain HTTP on a network you
  trust.
* The bridge has to be reachable under an address that the watch can
  resolve.  `homeassistant.local` may not resolve on the watch, so use the
  IP address or a real hostname.

## Updating

* The **bridge** is a container: pull the new image and restart it.
* The **integration** is updated through HACS, or by copying the new
  `custom_components/garmin_homeassistant` folder and restarting Home
  Assistant.
* The **watch application** is updated by installing a new `.prg` file.  The
  settings and the watch token survive the update, because they live in the
  storage of the application.

## Uninstalling

1. Remove the integration from *Settings* → *Devices & services*.
2. Stop and remove the bridge container.
3. Uninstall the application from the watch.

The bridge keeps nothing on disk, so removing it removes all of its state.

[Connect IQ SDK]: https://developer.garmin.com/connect-iq/download/
[Garmin Connect IQ store]: https://apps.garmin.com
