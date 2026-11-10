# Development

## The layout of the repository

```text
.
├── bridge/                      The bridge service
│   ├── src/garmin_bridge/      The Python package
│   ├── tests/                  The tests of the bridge
│   └── pyproject.toml          The dependencies and the tools of the bridge
├── custom_components/
│   └── garmin_homeassistant/   The Home Assistant integration
│       ├── tests/              The tests of the integration
│       └── quality_scale.yaml  The Home Assistant quality scale
├── watch/                       The Connect IQ application
│   ├── source/                 The shared Monkey C sources
│   ├── variants/               The notification presenters
│   ├── resources/              The strings, the settings and the icon
│   ├── tools/                  The launcher icon generator
│   └── build.sh                The build script
├── scripts/                     The helper scripts of the repository
├── docs/                        The documentation
├── requirements/                The pinned test requirements
└── .github/workflows/ci.yml     The CI pipeline
```

## Setting up

Two virtual environments are useful, because the bridge and the Home
Assistant integration have different dependencies.

```bash
# The bridge and the shared tools
python3 -m venv .venv
. .venv/bin/activate
pip install -e "bridge[test]"
pip install pytest-homeassistant-custom-component pytest-asyncio ruff mypy

# Or with uv
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e "bridge[test]"
```

The `Makefile` wraps the common commands:

```bash
make install     # install the development tools
make test        # run every test suite
make lint        # run ruff and mypy
make format      # format the sources
make watch-check # run the static checks of the Connect IQ sources
make watch-icon  # regenerate the launcher icon of the watch app
make brand       # regenerate the brand images
make image       # build the container image of the bridge
```

## Running the tests

```bash
# The bridge
cd bridge && python -m pytest tests -q

# The Home Assistant integration
python -m pytest custom_components/garmin_homeassistant/tests -q
```

The tests of the integration need the Home Assistant test harness.  The
pinned versions are in `requirements/ha-test.txt`.

```bash
pip install -r requirements/ha-test.txt
```

> `pycares` is held below 5.0 on purpose.  Version 5 starts a background
> thread that survives the shutdown of the event loop, which the Home
> Assistant test harness reports as a leaked thread.

The tests of the bridge use a fake Home Assistant, so they need neither a
real Home Assistant nor a network connection.

## The linters

```bash
ruff check custom_components scripts bridge/src bridge/tests
ruff format --check custom_components scripts bridge/src bridge/tests
mypy custom_components scripts
cd bridge && mypy src
```

The configuration lives in the root `pyproject.toml` for the integration and
the scripts, and in `bridge/pyproject.toml` for the bridge.

The type checker of the integration needs Home Assistant to be installed, so
run it in the environment that has the test requirements.  The
`compat.py` module keeps the few version differences between the supported
Home Assistant releases in one place.

## The watch application

### The static checks

The Connect IQ SDK is proprietary, so the watch application cannot be
compiled in an open source CI pipeline.  The repository ships a static
check instead:

```bash
python3 scripts/check_ciq.py
```

It verifies that

* the XML resources are well formed and reference each other correctly,
* every `$.Rez.Strings.*` and `$.Rez.Drawables.*` reference exists,
* the brackets of every Monkey C file are balanced,
* the classes that are used are defined,
* the manifest only targets the supported products and permissions,
* the shared sources do not use `Toybox.Notifications`, which only the Venu
  variant may use.

### Building it

```bash
export MONKEYC="$HOME/connectiq/bin/monkeyc"
export GARMIN_DEVELOPER_KEY="$HOME/.garmin/developer_key"
./watch/build.sh both
```

See [`watch/README.md`](../watch/README.md) for the details.

### The structure of the sources

| File | Content |
| --- | --- |
| `MyApp.mc` | The application class, the lifecycle and the notification channel. |
| `MainDelegate.mc` | The delegate that owns the screens. |
| `MainView.mc` | The three screens: entities, inbox and status. |
| `BridgeClient.mc` | The bridge API in the terms of the watch. |
| `HttpClient.mc` | The HTTP transport and the cache. |
| `EntityStore.mc` | The in-memory mirror of the entities and the notifications. |
| `Json.mc` | A small JSON parser. |
| `Settings.mc` | The user settings and the storage of the watch. |
| `Capabilities.mc` | The runtime detection of what the device can do. |
| `Values.mc` | The helpers that read the loosely typed values. |
| `BackgroundDelegate.mc` | The background service. |

Every class that is used in the background is marked with `(:background)`.
The runtime refuses a background service that uses a class that is not.

## The CI pipeline

`.github/workflows/ci.yml` has six jobs:

| Job | What it does |
| --- | --- |
| Bridge | The tests, ruff and mypy of the bridge. |
| Home Assistant integration | The tests, ruff and mypy of the integration. |
| Connect IQ sources | The static check of the Monkey C sources. |
| Hassfest | The validation of the integration by Home Assistant. |
| HACS | The validation of the repository by HACS. |
| Container image | The build of the bridge image. |

Two more workflows publish the software:

| Workflow | When | What it does |
| --- | --- | --- |
| `watch-build.yml` | A tag or a published release | Builds the watch application on a self hosted runner with the Connect IQ SDK and attaches the files to the release. |
| `release.yml` | A tag | Builds the image of the bridge and pushes it to the GitHub container registry. |

## The limitations of the pipeline

The watch application is **not compiled** by the pipeline.  The Connect IQ
SDK requires an account and a licence agreement, so it cannot be
redistributed or downloaded by a public runner.

The static check is a compromise, not a replacement for the compiler.  It
catches the mistakes that are easy to make, such as a missing resource, an
unbalanced bracket or a module that the Edge 1040 does not implement.  It
does not catch a type error or a wrong argument.

Every change to the watch application should therefore be tested on a real
device before it is released.

The release of the watch application is built by a **self hosted runner**
that has the SDK installed.  The setup of that runner is described in
[`../watch/README.md`](../watch/README.md).

## The house style

* The Python code is formatted with `ruff format` and passes `ruff check`.
* Every public function has a docstring that starts with a verb.
* The type hints are strict: `mypy` runs with `disallow_untyped_defs`.
* The comments explain *why*, not *what*.
* The documentation is written for the person who installs the thing, not
  for the person who wrote the code.
