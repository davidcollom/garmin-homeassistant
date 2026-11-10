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

### With the published image

Every release publishes the image to the GitHub container registry, so it can
be pulled without building it:

```bash
docker pull ghcr.io/davidcollom/garmin-homeassistant/bridge:latest
```

Use that image in the compose file instead of building it.

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

The watch application is a Connect IQ program.  There are two ways to get it
onto the watch: download the signed file from the release of this
repository, or install it from the Garmin Connect IQ store.

### From the release of this repository

Every release of this repository carries the two signed application files as
attachments:

| File | Devices | Notifications |
| --- | --- | --- |
| `venu.iq` | Venu 4 41 mm and 45 mm | with action buttons |
| `edge.iq` | Edge 1040 and Edge 1040 Solar | in the inbox of the application |

Download the file that matches your watch from the [releases] page and
install it:

1. Connect the watch to a computer over USB.  The watch appears as a drive.
2. Copy the `.iq` file into the `GARMIN/APPS` folder of that drive.
3. Eject the watch and restart it.

The application is now in the list of applications of the watch.  A sideloaded
application carries a small symbol, because it did not come from the Garmin
Connect IQ store.

To update, copy the new file over the old one and restart the watch.  The
settings and the watch token survive the update.

> The name of the file does not matter.  Naming it after the application id
> of the manifest, for example `03d13e1a-5c72-4b13-8e77-ebb94f9c4518.iq`,
> makes the versions easy to tell apart.

### From the Garmin Connect IQ store

When the application is published in the [Garmin Connect IQ store], install
it with the Garmin Connect app on the phone: *My Apps* → *Connect IQ* →
*Garmin Home Assistant* → *Install*.  The Garmin Connect app pushes the
application to the watch over Bluetooth and keeps it up to date.

The store route needs an account of the Garmin Connect IQ developer program,
which the maintainer of this repository uses to publish the application.

### Building it yourself

Building needs the [Connect IQ SDK], which is proprietary and has to be
downloaded from Garmin.  It also needs a developer key of the Garmin
Connect IQ developer program.

```bash
cd watch
export MONKEYC="$HOME/connectiq/bin/monkeyc"
export GARMIN_DEVELOPER_KEY="$HOME/.garmin/developer_key"
./build.sh venu           # the Venu 4, a signed .iq file
./build.sh edge           # the Edge 1040 and the Edge 1040 Solar
./build.sh both           # both
./build.sh both release   # both as .prg files for the store
```

The result is in `watch/build/`.  A debug build is a signed `.iq` file that
can be sideloaded, a release build is an unsigned `.prg` file for the
Connect IQ store.

The release of this repository is built by a self hosted runner that has the
SDK installed, because the SDK cannot be downloaded by a GitHub hosted
runner.  See [`../watch/README.md`](../watch/README.md) for the details.

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
[releases]: https://github.com/davidcollom/garmin-homeassistant/releases
