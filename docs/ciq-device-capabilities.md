# Garmin Connect IQ device capabilities — Venu 4 & Edge 1040

Research target: an open-source CIQ watch app talking to the `garmin-homeassistant` bridge
(FastAPI, `Authorization: Bearer <token>`, `X-Garmin-Watch-Id` header — see `bridge/src/garmin_bridge/app.py`).

Target devices: **Venu 4 41mm**, **Venu 4 45mm / D2 Air X15**, **Edge 1040 / Edge 1040 Solar**.

> `1040 Solar` = **Edge 1040 Solar**. There is no "Forerunner 1040 Solar".

---

## 1. Provenance and method

| Item | Value |
|---|---|
| SDK | Connect IQ SDK **9.3.0**, released **2026-10-20** |
| SDK index | <https://developer.garmin.com/downloads/connect-iq/sdks/sdks.json> |
| SDK archive used | `https://developer.garmin.com/downloads/connect-iq/sdks/connectiq-sdk-lin-9.3.0-2026-10-20-95888f262.zip` |
| Device DB (ground truth) | `monkeybrains.jar!com/garmin/monkeybrains/devices/devices.xml` (179 devices) |
| Online API docs | <https://developer.garmin.com/connect-iq/api-docs/> |
| Online core topics | <https://developer.garmin.com/connect-iq/core-topics/> |
| Compatible devices | <https://developer.garmin.com/connect-iq/compatible-devices/> |
| Device reference | <https://developer.garmin.com/connect-iq/device-reference/{edge1040,venu441mm,venu445mm}/> |

Legacy SDK URLs (`https://developer.garmin.com/sdk/connectiq/connectiq-sdk-<ver>.zip`) all return **404**;
the `sdks.json` manifest is the only working index.

**Method.** Two independent sources were used and cross-checked for every device-support claim:

1. The **Doxygen "Supported Devices"** lists (`<ul class="supported_devices">`) on each module page —
   authoritative per-module and per-function, parsed programmatically.
2. The **SDK `devices.xml`** device database — authoritative for product IDs, API-level grouping,
   resolution, touch, app types, memory limits, and per-device feature flags
   (`<notification>`, `<toast>`, `<solar>`, `<wifi_exclusions>`).

Where the two agree the claim is marked **VERIFIED**. Where a claim could not be sourced from
either, it is marked **UNVERIFIED** — see [§11](#11-unverified-items).

> Note on Doxygen semantics: a module page emits a "Supported Devices" list at **module level**
> plus one per **function that carries an explicit device filter**. A function with *no* list
> has no filter and is therefore available on every device that supports the module.

---

## 2. Device identity, product IDs and API level

Product IDs for `<iq:product id="..."/>` in `manifest.xml` — **VERIFIED** from `devices.xml`:

| Product ID | Marketing name | API level | `part_number` | Notes |
|---|---|---|---|---|
| `venu441mm` | Venu® 4 41mm | **6.0** | 006-B4644-00 | `family="round-390x390"` |
| `venu445mm` | Venu® 4 45mm / D2™ Air X15 | **6.0** | 006-B4643-00 | `family="round-454x454"` |
| `edge1040` | Edge® 1040 / **1040 Solar** | **6.0** | 006-B3843-00 | `family="rectangle-282x470"` |

**One product ID covers both Edge 1040 variants.** There is no `edge1040solar` product ID —
`devices.xml` names the device `"Edge® 1040 / 1040 Solar"` and carries
`<solar has_solar_support="true" />`. Use `<iq:product id="edge1040"/>` for both.

`devices.xml` attributes for `edge1040`:

```xml
<device id="edge1040" part_number="006-B3843-00" name="Edge® 1040 / 1040 Solar"
        family="rectangle-282x470" grouping="API level 6.0" web_doc_grouping="Edge">
```

Other part numbers found in `devices.xml` `part_numbers` blocks: `006-B3843-00` (fw 3135) and
`006-B4305-00` (fw 2456) for the Edge 1040; `006-B4643-00` + `006-B4944-00` for `venu445mm`.

### Official Compatible Devices table

Source: <https://developer.garmin.com/connect-iq/compatible-devices/> — **VERIFIED**

| Device | Resolution | Shape | Display | API |
|---|---|---|---|---|
| Venu® 4 41mm | 390 x 390 | round | AMOLED | 6.0 |
| Venu® 4 45mm / D2™ Air X15 | 454 x 454 | round | AMOLED | 6.0 |
| Edge® 1040 / 1040 Solar | 282 x 470 | rectangle | Transflective Liquid-Crystal (High Color) | 6.0 |
| Edge® 1050 / 1060 | 480 x 800 | rectangle | Transflective LCD (High Color) | 6.0 |
| Edge® 1030 (+ Plus / Bontrager) | 282 x 470 | rectangle | Transflective LCD (High Color) | 3.3 |
| Edge® 1000 / Explore | 240 x 400 | rectangle | Transflective LCD (High Color) | 2.4 |
| Venu® 3 | 454 x 454 | round | AMOLED | 5.2 |
| Venu® 3S | 390 x 390 | round | AMOLED | 5.2 |

**All three target devices are API level 6.0.** SDK 9.3.0 ships API level 6.0.x (`bin/api.db`
begins at `6.0.4`).

`minApiLevel` in the manifest controls device eligibility; **only major and minor are considered**
(1.2.1 is written to the manifest but 1.2 vs 1.2.x is irrelevant) —
<https://developer.garmin.com/connect-iq/core-topics/manifest-and-permissions/>.

---

## 3. Decisive answer: `Toybox.Notifications` on Edge 1040

> **Edge 1040 / Edge 1040 Solar does NOT support `Toybox.Notifications`.**
> **Venu 4 41mm and Venu 4 45mm DO.**
> Edge 1040 **does** support `Toybox.Communications`.

This is **device-gated, not merely API-level-gated**. The Edge 1040 is API level 6.0 (well above
the `Notifications` module's API 5.1.0 requirement) and is still excluded. Three independent
signals agree:

### 3.1 Doxygen module-level "Supported Devices" list — 70 devices, zero Edge

Source: <https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html>

The module is declared *"Since: API Level 5.1.0"*, *"Requires Permission: Notifications"*.
Its supported list contains **70** entries and **not a single Edge device**. Full list:

> Approach® S50 · Approach® S70 42mm · Approach® S70 47mm · Approach® S72 43mm
> Approach® S72 47mm · D2™ Mach 1 · D2™ Mach 2 Pro · D2™ Mach 2 · Descent™ G2
> Descent™ Mk3 43mm / Mk3i 43mm · Descent™ Mk3i 51mm · Enduro™ 3 · Enduro™ 4
> epix™ (Gen 2) / quatix® 7 Sapphire · epix™ Pro (Gen 2) 42mm
> epix™ Pro (Gen 2) 47mm / quatix® 7 Pro
> epix™ Pro (Gen 2) 51mm / D2™ Mach 1 Pro / tactix® 7 – AMOLED Edition · fēnix® 7 / quatix® 7
> fēnix® 7 Pro - Solar Edition (no Wi-Fi) · fēnix® 7 Pro · fēnix® 7S Pro · fēnix® 7S
> fēnix® 7X / tactix® 7 / quatix® 7X Solar / Enduro™ 2 · fēnix® 7X Pro - Solar Edition (no Wi-Fi)
> fēnix® 7X Pro · fēnix® 8 43mm
> fēnix® 8 47mm / 51mm / tactix® 8 47mm / 51mm / quatix® 8 47mm / 51mm
> fēnix® 8 Pro 47mm / 51mm / MicroLED / quatix® 8 Pro 47mm / 51mm · fēnix® 8 Solar 47mm
> fēnix® 8 Solar 51mm / tactix® 8 Solar 51mm · fēnix® 9 43mm · fēnix® 9 47mm / 51mm
> fēnix® 9 Pro 43mm · fēnix® 9 Pro 47mm · fēnix® 9 Pro 51mm · fēnix® 9 Pro Solar 47mm
> fēnix® 9 Pro Solar 51mm · fēnix® E · Forerunner® 165 Music · Forerunner® 165
> Forerunner® 170 Music · Forerunner® 170 · Forerunner® 255 Music · Forerunner® 255
> Forerunner® 255s Music · Forerunner® 255s · Forerunner® 265 · Forerunner® 265s
> Forerunner® 570 42mm · Forerunner® 570 47mm · Forerunner® 70 · Forerunner® 955 / Solar
> Forerunner® 965 · Forerunner® 970 · Instinct® 3 AMOLED 45mm · Instinct® 3 AMOLED 50mm
> Instinct® 3 Solar 45mm / 50mm · Instinct® Crossover AMOLED · Instinct® E 40mm
> Instinct® E 45mm
> MARQ® (Gen 2) Athlete / Adventurer / Captain / Golfer / Carbon Edition / Commander - Carbon Edition
> MARQ® (Gen 2) Aviator
> MARQ® (Gen 3) Athlete / Adventurer / Aviator / Commander / Golfer / Diver · Venu® 3 · Venu® 3S
> **Venu® 4 41mm** · **Venu® 4 45mm / D2™ Air X15** · Venu® X1 · vívoactive® 5 · vívoactive® 6

**Venu® 4 41mm, Venu® 4 45mm / D2™ Air X15, Venu® 3 and Venu® 3S are present. No Edge device is.**

### 3.2 SDK `devices.xml` feature flags — the independent cross-check

`devices.xml` carries a per-device `<notification>` element only on devices that implement the
notification system. Extracted from the SDK's own device DB (**179 devices**):

| Device | `<toast>` element | `<notification>` element |
|---|---|---|
| `edge1040` | **present** (`<toast x="7" y="7" w="264" h="55" type="partial">`) | **absent** |
| `venu441mm` | present (`type="background"`) | **present** (`type="fullscreen" mode="preview" show_icon="true"`) |
| `venu445mm` | present (`type="background"`) | **present** (`type="fullscreen" mode="preview" show_icon="true"`) |

Across the 179-device DB, **60 devices** carry a `<notification>` element and **110** carry a
`<toast>` element. **`edge1040` and `edge1050` carry neither a `<notification>` nor any
notification capability** — the `<notification>` element is absent for both, while `<toast>` is
present. This matches the Doxygen list exactly.

### 3.3 Consequence for the design

The Edge 1040's *notification-capable* surface is instead:

| API | Edge 1040 supported? | Source |
|---|---|---|
| `Toybox.Notifications.showNotification` | **No** | <https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html> |
| `Toybox.Notifications.registerForNotificationMessages` | **No** | same |
| `Toybox.WatchUi.showToast` | **Yes** (112-device list incl. Edge® 1040 / 1040 Solar) | <https://developer.garmin.com/connect-iq/api-docs/Toybox/WatchUi.html> |
| `Toybox.Background.requestApplicationWake` | **Yes** (module list, 168 devices incl. Edge 1040) | <https://developer.garmin.com/connect-iq/api-docs/Toybox/Background.html> |
| `Toybox.Attention.vibrate` | **No** (150-device list, no Edge) | <https://developer.garmin.com/connect-iq/api-docs/Toybox/Attention.html> |
| `Toybox.Attention.backlight` | **Yes** (178-device list incl. Edge 1040) | same |
| `Toybox.Attention.playTone` | **Yes** (155-device list incl. Edge 1040) | same |

So a **cross-platform design must feature-detect**, not branch on API level:

- **Venu 4** → `Notifications.showNotification(...)` with `:actions` for actionable HA alerts.
- **Edge 1040** → `WatchUi.showToast(...)` (text + optional icon only, **no action buttons**)
  and/or `Background.requestApplicationWake(...)` (a yes/no confirm dialog).

`WatchUi.showToast` signature — **VERIFIED**:

```monkey-c
showToast(text as Lang.String or Lang.ResourceId,
          options as { :icon as WatchUi.BitmapResource or Graphics.BitmapReference or Lang.ResourceId } or Null) as Void
```

`Toybox.Attention` has no `Edge® 1000 / Explore`, `Edge® 1030`, `Edge® 1040 / 1040 Solar`,
`Edge® 1050` or `Edge® 1060` entries for `vibrate`, `hasFlashlightColor` or `setFlashlightMode`.

### 3.4 Permission inconsistency (Garmin's own docs disagree)

- The `Notifications` **module page** states *"Requires Permission: Notifications"* — **VERIFIED**.
- Garmin's **own SDK sample** `samples/Notifications/manifest.xml` declares
  `<iq:uses-permission id="Notifications"/>` — **VERIFIED** (SDK-local file).
- But the **Manifest and Permissions** article's permission table does **not** list
  `Notifications` at all. Its entries are: Ant, AudioInput, AudioOutput, Background,
  BluetoothLowEnergy, Communications, ComplicationProvider, ComplicationSubscriber,
  Data Field Alert, Fit, PersistedContent, Positioning, Sensor, SensorHistory, SensorLogging,
  UserProfile — **VERIFIED**
  (<https://developer.garmin.com/connect-iq/core-topics/manifest-and-permissions/>).

**Practical guidance:** declare `<iq:uses-permission id="Notifications"/>` in the manifest.
It is harmless where the permission is not recognised and required where it is. Because the
permission is not in the published table, the *user-facing* install prompt behaviour for it is
**UNVERIFIED**.

---

## 4. Per-module / per-function device support matrices

All lists parsed from the Doxygen `Supported Devices` blocks. "Edge 10xx" column =
Edge® 1000/Explore, 1030 (+Plus/Bontrager), 1040/1040 Solar, 1050, 1060, 540/550/840/850/Explore 2/3.

### 4.1 `Toybox.Communications` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/Communications.html>

Module-level list: **180 devices** — includes **Edge® 1040 / 1040 Solar** (and 1050, 1060,
Edge 1000, 1030 family), **Venu® 3, Venu® 3S, Venu® 4 41mm, Venu® 4 45mm / D2™ Air X15**.
Requires Permission: **Communications**.

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| *module level* | 180 | **Yes** | Yes | Yes |
| `makeWebRequest` | *(no filter → module list)* | **Yes** | Yes | Yes |
| `makeJsonRequest` | 180 *(identical to module list)* | **Yes** | Yes | Yes |
| `makeImageRequest`, `makeOAuthRequest`, `openWebPage`, `encodeURL`, `generateSignedOAuthHeader`, `cancelAllRequests`, `checkWifiConnection`, `enableConnection`, `disableConnection` | *(no filter → module list)* | **Yes** | Yes | Yes |
| `registerForPhoneAppMessages` | 168 | **Yes** | Yes | Yes |
| `registerForPhoneAppMessageErrors` | 46 | **Yes** | **No** | Yes |
| `transmit` | 169 | **Yes** | Yes | Yes |
| `notifySyncComplete` | 119 | **Yes** | Yes | Yes |
| `notifySyncProgress` | 119 | **Yes** | Yes | Yes |
| `startSync` | 119 | **Yes** | Yes | Yes |
| `startSync2` | 78 | **Yes** | Yes | Yes |
| `emptyMailbox` | 153 | **No** | Yes | Yes |
| `getMailbox` | 153 | **No** | Yes | Yes |
| `setMailboxListener` | 153 | **No** | Yes | Yes |
| `checkLteConnection` | 7 | No | No | No |

**Takeaway:** the **entire HTTP path (`makeWebRequest`) works on the Edge 1040**. The legacy
mailbox APIs (`getMailbox`/`setMailboxListener`/`emptyMailbox`) do **not** — do not use them.

### 4.2 `Toybox.Background` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/Background.html>

Module-level list: **168 devices** — includes Edge 1040/1040 Solar, Venu 3/3S, Venu 4 41/45.
Requires Permission: **Background**.

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| *module level* | 168 | **Yes** | Yes | Yes |
| `registerForPhoneAppMessageEvent` | 138 | **Yes** | Yes | Yes |
| `getPhoneAppMessageEventRegistered` | 138 | **Yes** | Yes | Yes |
| `deletePhoneAppMessageEvent` | 138 | **Yes** | Yes | Yes |

`registerForTemporalEvent`, `requestApplicationWake`, `Background.exit`, `getBackgroundData`,
`getLastTemporalEventTime`, `getTemporalEventRegisteredTime` and the other event
register/delete functions carry **no device filter** → available on all module devices
(**Edge 1040 included**).

### 4.3 `Toybox.Sensor` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/Sensor.html>

Module-level list: **180 devices** (includes Edge 1040, Venu 3/3S, Venu 4 41/45).

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| *module level* | 180 | Yes | Yes | Yes |
| `getMaxSampleRate` | 164 | Yes | Yes | Yes |
| `getMaxSampleRateForSensorType` | 105 | Yes | Yes | Yes |
| `registerSensorDataListener` | 164 | Yes | Yes | Yes |
| `unregisterSensorDataListener` | 164 | Yes | Yes | Yes |
| `notifyNewSensor`, `notifyPairComplete`, `notifyUnpairComplete`, `notifyScanComplete`, `notifyError` | 82 | Yes | Yes | Yes |

Requires Permission: **Sensor**.

### 4.4 `Toybox.System` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/System.html>

The module page carries **no module-level device list**; only one function does:

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| `getDisplayMode` | 54 | **No** | Yes | Yes |

`getDisplayMode` is documented as *"only available in devices with AMOLED or LCD screens"* —
the Edge 10xx are transflective/MIP, so they are excluded. **All other `System` functions
(`getDeviceSettings`, `getSystemStats`, `getSystemTime`, …) carry no device filter** and are
therefore available on the Edge 1040.

### 4.4.1 `System.getDeviceSettings()` and `System.getSystemStats()`

Sources: <https://developer.garmin.com/connect-iq/api-docs/Toybox/System/DeviceSettings.html>,
<https://developer.garmin.com/connect-iq/api-docs/Toybox/System/Stats.html>

`System.getDeviceSettings() as System.DeviceSettings` (API 1.0.0) — key members for this project:
`screenWidth`, `screenHeight`, `screenShape`, `isTouchScreen`, `partNumber`, `monkeyVersion`,
`firmwareVersion`, `notificationCount`, `inputButtons`, `connectionAvailable`, `connectionInfo`,
`phoneConnected`, `fontScale`, `is24Hour`, `isGlanceModeEnabled`, `doNotDisturb`.

`System.getSystemStats() as System.Stats` — `getSystemStats()` is **API 1.0.0**; the individual
`Stats` members have their own levels:

| `Stats` member | Type | Since | Notes |
|---|---|---|---|
| `battery` | `Lang.Float` | 1.0.0 | remaining battery % |
| `freeMemory` | `Lang.Number` | 1.0.0 | bytes |
| `totalMemory` | `Lang.Number` | 1.0.0 | bytes |
| `usedMemory` | `Lang.Number` | 1.0.0 | bytes used by the app |
| `charging` | `Lang.Boolean` | **3.0.0** | *"set to true if the device is connected to the charging cradle or cable **whether or not the device is fully charged**"* |
| `solarIntensity` | `Lang.Number or Null` | **3.2.0** | 0–100 charge efficiency; *"Will be set to null if the device doesn't support solar or a negative number when…"* |
| `batteryInDays` | `Lang.Float` | 3.3.0 | |

→ `System.getSystemStats().charging` is available for app-level charging policy — the practical
substitute for the undocumented battery-vs-charging background rule (§7.6).
`System.getSystemStats().solarIntensity` exists in the API but its availability on the
Edge 1040 Solar is **UNVERIFIED**.

### 4.5 `Toybox.UserProfile` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/UserProfile.html>

No module-level list; both documented functions carry explicit lists of **41 devices**:

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| `getFunctionalThresholdPower` | 41 | **Yes** | **No** | Yes |
| `getPowerZones` | 41 | **Yes** | **No** | Yes |

Edge entries present: Edge® 1040 / 1040 Solar, Edge® 1050, Edge® 1060, Edge® 540 / 540 Solar,
Edge® 550, Edge® 840 / 840 Solar, Edge® 850, Edge® Explore 3, Edge® Explore 3 Plus, Edge® MTB.
Note **Venu® 3 / 3S are excluded** here even though Venu 4 is included.

### 4.6 `Toybox.PersistedContent` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/PersistedContent.html>

Module-level list: **159 devices** (includes Edge 1040, Venu 3/3S, Venu 4 41/45).

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| *module level* | 159 | Yes | Yes | Yes |
| `getWaypoints` / `saveWaypoint` | 155 | Yes | Yes | Yes |
| `getAppWaypoints` | 152 | Yes | Yes | Yes |
| `getAppWorkouts` | 145 | Yes | Yes | Yes |
| `getWorkouts` | 148 | Yes | Yes | Yes |
| `getCourses` | 133 | Yes | No | Yes |
| `getAppCourses` | 130 | Yes | No | Yes |
| `getRoutes` / `getAppRoutes` | 59 | Yes | No | **No** |
| `getTracks` / `getAppTracks` | 6 | No | No | No |

Requires Permission: **PersistedContent**.

### 4.7 `Toybox.WatchUi` — <https://developer.garmin.com/connect-iq/api-docs/Toybox/WatchUi.html>

No module-level list. Per-function:

| Function | Device count | Edge 1040? | Venu 3? | Venu 4? |
|---|---:|:---:|:---:|:---:|
| `showToast` | 112 | **Yes** | Yes | Yes |
| `showActionMenu` | 101 | **No** | Yes | Yes |
| `makeReviewTokenRequest` | 90 | **No** | Yes | Yes |
| `startUserReview` | 90 | **No** | Yes | Yes |
| `configureTouchEvents` | 54 | **No** | Yes | Yes |
| `getTouchEventsConfiguration` | 54 | **No** | Yes | Yes |
| `getSubscreen` | 7 | No | No | No |

Edge entries present for `showToast`: Edge® 1040 / 1040 Solar, Edge® 1050, Edge® 1060,
Edge® 540 / 540 Solar, Edge® 550, Edge® 840 / 840 Solar, Edge® 850, Edge® Explore 2,
Edge® Explore 3, Edge® Explore 3 Plus, Edge® MTB.

**`showActionMenu` is not available on the Edge 1040** — do not build a UI that depends on it.

---

## 5. `Toybox.Communications` HTTP API reference

Source: <https://developer.garmin.com/connect-iq/api-docs/Toybox/Communications.html>
Core topics: <https://developer.garmin.com/connect-iq/core-topics/https/> (JSON REST Requests),
<https://developer.garmin.com/connect-iq/core-topics/communicating-with-mobile-apps/>,
<https://developer.garmin.com/connect-iq/core-topics/authenticated-web-services/>

### 5.1 `makeWebRequest` — exact signature

```monkey-c
makeWebRequest(
    url as Lang.String,
    parameters as Lang.Dictionary<Lang.Object, Lang.Object> or Null,
    options as {
        :method as Communications.HttpRequestMethod,
        :headers as Lang.Dictionary,
        :body as Lang.String or Lang.ByteArray,
        :responseType as Communications.HttpResponseContentType,
        :context as Lang.Object or Null,
        :maxBandwidth as Lang.Number,
        :fileDownloadProgressCallback as Lang.Method(totalBytesTransferred as Lang.Number,
                                                    fileSize as Lang.Number or Null) as Void
    } or Null,
    responseCallback as Lang.Method(responseCode as Lang.Number,
                                   data as Communications.ContentType or Null) as Void
    or Lang.Method(responseCode as Lang.Number,
                   data as Communications.ContentType or Null,
                   context as Lang.Object) as Void
) as Void
```

*Since: API Level 1.3.0.* Throws `Lang.InvalidOptionsException` (missing required option) and
`Lang.SymbolNotAllowedException` (`:responseType` unsupported on the device).

### 5.2 Option keys — complete, with the traps

| Key | Type | Notes (verbatim-derived) |
|---|---|---|
| `:method` | `HttpRequestMethod` | "This should be an HTTP_REQUEST_METHOD_* value." |
| `:headers` | `Lang.Dictionary` | HTTP headers. **Content-Type goes here — there is no `:contentType` option.** The `"Content-Type"` header may be a `REQUEST_CONTENT_TYPE_*` value **or a String since CIQ 6.0.3**. If unset it defaults to `application/json` for GET/DELETE and `application/x-www-form-urlencoded` for POST/PUT. **DELETE** params are appended to the URL by default; setting DELETE **and** a `"Content-Type"` header moves params into the body. **GET** params are always URL-appended — a `Content-Type` header does *not* create a body. |
| `:body` | `Lang.String` or `Lang.ByteArray` | **Since CIQ 6.0.3.** "The body of the request, parameters if provided will be url-encoded and appended to the request url" |
| `:responseType` | `HttpResponseContentType` | `HTTP_RESPONSE_CONTENT_TYPE_*`. If omitted, the server's `Content-Type` header decides; an unknown type ⇒ error. FIT/GPX responses are parsed and stored on the device. |
| `:context` | `Lang.Object` | Opaque user object. **If populated, the callback must accept a third parameter.** |
| `:maxBandwidth` | `Lang.Number` | Only effective when processing **HLS** content. |
| `:fileDownloadProgressCallback` | `Lang.Method` | **Since CIQ 3.2.0.** Media file download progress only. `fileSize` may be `null`. |
| `:mediaEncoding` | `Media.Encoding` | **Documented in the parameter prose but ABSENT from the `options` typedef.** Treat as **UNVERIFIED** whether it is accepted at runtime. |

There is **no `:timeout` option** — the only timeout control is the `NETWORK_REQUEST_TIMED_OUT`
(-300) error. Verified absent from the signature and from the option list.

### 5.3 Response callback

```monkey-c
function onReceive(responseCode as Number, data as Dictionary?) as Void {
    if (responseCode == 200) { ... }
}
```

* `responseCode` — the **HTTP status code**, or a **`BLE_*` / `NETWORK_*` / `REQUEST_*` error constant**
  (negative) on failure.
* `data` — deserialised content on success, `null` on failure.
  `Communications.ContentType` is typedef'd as
  **`Lang.Dictionary or Lang.String or PersistedContent.Iterator or Lang.ByteArray`**.
  → **A JSON response arrives as a `Lang.Dictionary`.**
* With `:context` populated, the callback takes **three** parameters
  `(responseCode, data, context)`.

### 5.4 Constants

`Communications.HttpRequestMethod` (enum, API 1.2.0):

| Constant | Value |
|---|---|
| `HTTP_REQUEST_METHOD_GET` | 1 |
| `HTTP_REQUEST_METHOD_PUT` | 2 |
| `HTTP_REQUEST_METHOD_POST` | 3 |
| `HTTP_REQUEST_METHOD_DELETE` | 4 |

`Communications.HttpResponseContentType` (enum):

| Constant | Value | Since |
|---|---|---|
| `HTTP_RESPONSE_CONTENT_TYPE_JSON` | 0 | 1.3.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_URL_ENCODED` | 1 | 1.3.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_GPX` | 2 | 2.2.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_FIT` | 3 | 2.2.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_AUDIO` | 4 | 3.0.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_TEXT_PLAIN` | 5 | 3.0.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_HLS_DOWNLOAD` | 6 | 3.0.10 |
| `HTTP_RESPONSE_CONTENT_TYPE_ANIMATION_MANIFEST` | 7 | 3.1.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_ANIMATION` | 8 | 3.1.0 |
| `HTTP_RESPONSE_CONTENT_TYPE_OCTET_STREAM` | 10 | **6.0.3** |

> Note the gap: there is **no value 9**.

`Communications.HttpRequestContentType` (enum) — the request body content type:

| Constant | Value | Since |
|---|---|---|
| `REQUEST_CONTENT_TYPE_URL_ENCODED` | 0 | 1.2.0 |
| `REQUEST_CONTENT_TYPE_JSON` | 1 | 1.2.0 |

### 5.5 Error constants (`Communications.Error`)

| Constant | Value | Meaning |
|---|---|---|
| `UNKNOWN_ERROR` | 0 | An unknown error has occurred. |
| `BLE_ERROR` | -1 | A generic BLE error has occurred. |
| `BLE_HOST_TIMEOUT` | -2 | We timed out waiting for a response from the host. |
| `BLE_SERVER_TIMEOUT` | -3 | We timed out waiting for a response from a server. |
| `BLE_NO_DATA` | -4 | Response contained no data. |
| `BLE_REQUEST_CANCELLED` | -5 | The request was cancelled at the request of the system. |
| `BLE_QUEUE_FULL` | -101 | Too many requests have been made. |
| `BLE_REQUEST_TOO_LARGE` | -102 | **Serialized input data for the request was too large.** |
| `BLE_UNKNOWN_SEND_ERROR` | -103 | Send failed for an unknown reason. |
| `BLE_CONNECTION_UNAVAILABLE` | -104 | No BLE connection is available. |
| `INVALID_HTTP_HEADER_FIELDS_IN_REQUEST` | -200 | Request contained invalid http header fields. |
| `INVALID_HTTP_BODY_IN_REQUEST` | -201 | Request contained an invalid http body. |
| `INVALID_HTTP_METHOD_IN_REQUEST` | -202 | Request used an invalid http method. |
| `NETWORK_REQUEST_TIMED_OUT` | -300 | Request timed out before a response was received. |
| `INVALID_HTTP_BODY_IN_NETWORK_RESPONSE` | -400 | Response body data is invalid for the request type. |
| `INVALID_HTTP_HEADER_FIELDS_IN_NETWORK_RESPONSE` | -401 | Response contained invalid http header fields. |
| `NETWORK_RESPONSE_TOO_LARGE` | -402 | **Serialized response was too large.** |
| `NETWORK_RESPONSE_OUT_OF_MEMORY` | -403 | Ran out of memory processing network response. (3.0.0) |
| `STORAGE_FULL` | -1000 | Filesystem too full to store response data. (2.2.0) |
| `SECURE_CONNECTION_REQUIRED` | -1001 | **Indicates an https connection is required for the request.** (2.3.0) |
| `UNSUPPORTED_CONTENT_TYPE_IN_RESPONSE` | -1002 | Content type given in response is not supported or does not match what is expected. (2.4.1) |
| `REQUEST_CANCELLED` | -1003 | Http request was cancelled by the system. (2.4.2) |
| `REQUEST_CONNECTION_DROPPED` | -1004 | Connection was lost before a response could be obtained. (3.0.0) |
| `UNABLE_TO_PROCESS_MEDIA` | -1005 | Downloaded media file was unable to be read. (3.0.2) |
| `UNABLE_TO_PROCESS_IMAGE` | -1006 | Downloaded image file was unable to be processed. (3.0.3) |
| `UNABLE_TO_PROCESS_HLS` | -1007 | HLS content could not be downloaded. (3.0.10) |

> **UNVERIFIED:** the *byte* thresholds behind `BLE_REQUEST_TOO_LARGE` (-102) and
> `NETWORK_RESPONSE_TOO_LARGE` (-402) are **not published** anywhere in Garmin's public docs
> or in the SDK. Only the error descriptions above exist. Design the payload to be small
> (a few KB) and handle both codes explicitly.

### 5.6 Transport, proxy and HTTPS

* **Bluetooth proxy.** `makeWebRequest` is documented: *"This method can be used when connected to
  WiFi or a mobile device over Bluetooth."* The JSON REST core topic states the phone
  *"may act as a bridge between the app and the Internet"* and that calls are
  *"converted to serialized Monkey C data and sent across the BLE pipe"* — i.e. when the watch
  has no internet route of its own the request is proxied **through the paired phone's
  Garmin Connect Mobile** over BLE.
* **Device WiFi.** The Edge 1040 and Venu 4 have WiFi. `devices.xml` records
  `wifi_exclusions` for these devices:
  * `venu441mm`, `venu445mm`: `<wifi_exclusions normal="true" />`
  * `edge1040`: `<wifi_exclusions fit_recording="true" />`
  The Venu 4 exclusion `normal="true"` means the **normal (non-fitness) WiFi profile is
  excluded**, i.e. direct WiFi use is not generally available on Venu 4 for ordinary apps.
  Interpretation of the exact exclusion semantics is **UNVERIFIED**.
* **HTTPS is required** for the HA bridge — `SECURE_CONNECTION_REQUIRED` (-1001) exists precisely
  to signal this. Always use `https://`.
* **`Authorization` header.** Supported via `:headers`. For OAuth 1.0a there is a helper
  `generateSignedOAuthHeader(url, params, requestMethod, signatureMethod, token, tokenSecret,
  consumerKey, consumerSecret) as Lang.String` which returns *"the value for the 'Authorization'
  header in an OAuth 1.0a request"* — note it returns only the **value**, so you must place it
  yourself: `:headers => { "Authorization" => Communications.generateSignedOAuthHeader(...) }`.
  `generateSignedOAuthHeader` and `makeOAuthRequest` are marked **deprecated**.
* **Bearer tokens (the HA bridge case)** are a plain header:
  `:headers => { "Authorization" => "Bearer <watch_token>" }`.

### 5.7 Canonical request shape for this project

The bridge already speaks `Authorization: Bearer <token>` and an `X-Garmin-Watch-Id` header
(`bridge/src/garmin_bridge/app.py`). The CIQ side:

```monkey-c
import Toybox.Communications;
import Toybox.System;

const BRIDGE_URL = "https://home.example.lan:8099";

function onResponse(responseCode as Number, data as Dictionary?) as Void {
    if (responseCode == 200 && data != null) {
        // data["e"] -> entity list, data["rev"] -> revision
    } else if (responseCode == Communications.NETWORK_RESPONSE_TOO_LARGE) {
        // shrink the query
    } else {
        System.println("bridge error: " + responseCode);
    }
}

function fetchEntities() as Void {
    var options = {
        :method => Communications.HTTP_REQUEST_METHOD_GET,
        :headers => {
            "Authorization" => "Bearer " + Application.PROPERTY_WATCH_TOKEN,
            "X-Garmin-Watch-Id" => Application.PROPERTY_WATCH_ID
        },
        :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON
    };
    Communications.makeWebRequest(BRIDGE_URL + "/v1/entities", null, options, method(:onResponse));
}
```

---

## 6. `Toybox.Notifications` API reference (Venu 4 only — see §3)

Source: <https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html>
Core topic: <https://developer.garmin.com/connect-iq/core-topics/notifications/>

Module: **API Level 5.1.0**. Requires Permission: **Notifications**.

### 6.1 `showNotification`

```monkey-c
showNotification(
    title as Lang.String or Lang.ResourceId,
    subTitle as Lang.String or Lang.ResourceId,
    options as Notifications.ShowNotificationOptions or Null
) as Void
```

`ShowNotificationOptions` typedef:

```monkey-c
{
    :icon as WatchUi.BitmapResource or Graphics.BitmapReference or Lang.ResourceId,
    :body as Lang.String or Lang.ResourceId,
    :data as Notifications.NotificationDataType,
    :actions as Lang.Array<Notifications.Action>,
    :dismissPrevious as Lang.Boolean
}
```

| Option | Behaviour |
|---|---|
| `:body` | The body of the notification. |
| `:data` | Data associated with the notification. *"Will be passed back to the application for context when a notification action is selected."* |
| `:icon` | Icon to display. If none supplied and the system requires one, the **app icon** is used. |
| `:actions` | Array of `Action` — `{ :label as Lang.String, :data as Notifications.NotificationDataType }`. *"An empty :action array with no :data will appear as an actionless notification. These notifications will not trigger a notification when dismissed."* |
| `:dismissPrevious` | *"If true, dismiss all prior notifications that the app has posted. Note that this **defaults to true** if not provided."* |

### 6.2 `registerForNotificationMessages`

```monkey-c
registerForNotificationMessages(callback as Notifications.NotificationMessageCallback or Null) as Void
// NotificationMessageCallback as Lang.Method(message as Notifications.NotificationMessage) as Void
```

*"Register a callback for receiving notification messages. The callback will be called once for
each notification message. If there are messages queued for the app when this function is called,
the callback will immediately be called once for each pending message."*

### 6.3 `NotificationMessage` fields

| Field | Meaning |
|---|---|
| `type` | `NOTIFICATION_MESSAGE_TYPE_DISMISSED` = **1** ("The notification was dismissed by the user") or `NOTIFICATION_MESSAGE_TYPE_SELECTED` = **2** ("The notification action was selected by the user") |
| `data` | The notification's `:data` |
| `action` | The selected action's `:data` |

> `NotificationMessage` is a separate class page under the module
> (`Classes Under Namespace: Classes: NotificationMessage`). Its field list is not reproduced in
> the module page body but is confirmed by the module's own example and the core topic.

### 6.4 Action delivery — two independent paths

1. **Launch path.** The core topic states: *"If the user selects one of these actions, the
   `state` dictionary of your `AppBase.onStart()` is called with **`:launchedFromNotification`**
   containing the action data."*
   → Read `state[:launchedFromNotification]` in `AppBase.onStart()`.
   *Caveat:* the `:launchedFromNotification` key appears **only** in the online core topic.
   The Doxygen `AppBase.onStart()` page does not document it, and Garmin's own Notifications
   sample uses `registerForNotificationMessages` rather than `onStart` state. Treat the
   `onStart` route as **documented but not Doxygen-confirmed** — implement the callback route
   as primary.

2. **Callback path.** `registerForNotificationMessages` fires with
   `type == NOTIFICATION_MESSAGE_TYPE_SELECTED` and `action == <selected action's :data>`.

   **The core topic's own example registers the callback as:**
   > *"// register callback to start receiving notifications when users interact with notifications
   > **or toasts**"*

   → The callback channel is shared with the toast channel. This is the practical hook to use
   on **both** Venu 4 and Edge 1040, if the module were available — it is **not** available on
   Edge 1040, so Edge 1040 must rely on `WatchUi.showToast` (display only, **no actions**).

### 6.5 Can users action notifications on-watch?

**Yes — on devices that support the module.** The core topic is explicit:

> *"You are allowed to define an array of actions with the notification. The actions are defined
> as a string and serializable data. The action strings are presented to the user with the
> notification. If the user selects one of these actions, the `state` dictionary of your
> `AppBase.onStart()` is called with `:launchedFromNotification` containing the action data.
> **By default, the notification has a launch and dismiss action associated with it.** Using the
> `:data` option allows you to associate data with the default action."*

The Garmin sample (`samples/Notifications/source/NotificationsApp.mc`) uses exactly this shape:

```monkey-c
Notifications.showNotification("Jeff", "Something Happened", {
    :icon => Rez.Drawables.EmergencyIcon,
    :data => {},
    :actions => [
        { :label => Rez.Strings.ReplyAction,  :data => MY_NOTIFICATION_ID_REPLY },
        { :label => Rez.Strings.ForwardAction, :data => MY_NOTIFICATION_ID_FORWARD },
    ],
});
```

Presentation caveat: *"The presentation will match the personality of the device, and is not
guaranteed to display the same across different devices. If multiple notifications are present,
the most recent notification will be displayed."*

### 6.6 Reference pattern: raising a notification from a background service

Garmin's own sample (`samples/Notifications/source/BackgroundDelegate.mc`) shows the intended
architecture — **post the notification directly from the background service**, and let the
foreground app receive the user's reply through the registered callback:

```monkey-c
(:background)
class BackgroundDelegate extends System.ServiceDelegate {
    function onTemporalEvent() as Void {
        var options = {
            :body => Rez.Strings.backgroundBody,
            :data => { DataKeys.SOURCE => "background" } as Dictionary<Number, String>,
            :actions => [
                { :label => Rez.Strings.notificationOption1, :data => NotificationOptions.OPTION_1 },
                { :label => Rez.Strings.notificationOption2, :data => NotificationOptions.OPTION_2 }
            ] as Array<Notifications.Action>
        };
        Notifications.showNotification(Rez.Strings.backgroundTitle, Rez.Strings.backgroundSubtitle, options);
    }
}
```

Note: `showNotification` is called **without** a prior `Background.exit()` — the background
service simply posts the notification and ends.

The foreground side of the same sample confirms the callback contract:

```monkey-c
Notifications.registerForNotificationMessages(method(:onNotification));

function onNotification(message as Notifications.NotificationMessage) as Void {
    switch (message.type) {
        case Notifications.NOTIFICATION_MESSAGE_TYPE_SELECTED:
            switch (message.action as Number) { ... }   // the selected action's :data
            break;
        case Notifications.NOTIFICATION_MESSAGE_TYPE_DISMISSED:
            ...
            break;
    }
    var source = (message.data as Dictionary)[DataKeys.SOURCE] as String;   // the notification's :data
}
```

**Important detail:** the sample registers the callback inside **`getInitialView()`**, not in
`initialize()` — with the comment *"Since this function is called only when running in the
foreground, register for notifications here"*. Registering from the background service would
fail, because the background service has a much smaller memory pool (§7.6) and the `(:background)`
scope excludes foreground-only code.

Also note the sample's `onStart(state as Dictionary?)` **does not read `:launchedFromNotification`**
— it only calls `Background.registerForTemporalEvent(...)`. This corroborates the caveat in
§6.4: the callback route is the one Garmin actually ships.

---

## 7. `Toybox.Background` rules

Source: <https://developer.garmin.com/connect-iq/api-docs/Toybox/Background.html>
Core topic: <https://developer.garmin.com/connect-iq/core-topics/backgrounding/>

Module: **API Level 2.3.0**. Requires Permission: **Background**. Available on Edge 1040 and
Venu 4 (§4.2).

### 7.1 Event registry

| Event | Register with | API level |
|---|---|---|
| Activity Completed | `Background.registerForActivityCompletedEvent()` | 3.1.0 |
| Goal | `Background.registerForGoalEvent()` | 2.3.0 |
| OAuth Response | `Background.registerForOAuthResponseEvent()` | 2.3.0 |
| Phone App Message | `Background.registerForPhoneAppMessageEvent()` | 3.2.0 |
| Sleep | `Background.registerForSleepEvent()` | 2.3.0 |
| Steps | `Background.registerForStepsEvent()` | 2.3.0 |
| **Temporal** | `Background.registerForTemporalEvent()` | 2.3.0 |

### 7.2 `registerForTemporalEvent` — the 5-minute rule

```monkey-c
registerForTemporalEvent(time as Time.Moment or Time.Duration) as Void
```

Throws `Background.InvalidBackgroundTimeException`:
> *"Indicates an application has attempted to schedule a background event which either:
> * Occurs less than five minutes after the last background event occurred
> * Has a duration of less than five minutes"*

The core topic confirms the cadence: *"Allows your service to be woken at a specific time or
repeatedly at a certain interval (**up to every five minutes**)"*.

Helper: `getLastTemporalEventTime() as Time.Moment or Null` — *"This is useful for ensuring new
events are not scheduled within the five minute minimum time allowed between temporal events."*
Its documented example registers the next event at `lastTime + 5 min`. Note also
`getTemporalEventRegisteredTime()` returns the Moment/Duration the event was registered with.

**Only one temporal event is active at a time** (`deleteTemporalEvent()` removes it).

> The `Moment` form schedules at a specific instant; using a `Moment` (rather than a `Duration`)
> means the 5-minute *duration* restriction does not apply, so a specific-time schedule is not
> rejected for being under 5 minutes out. The precise interaction is **UNVERIFIED** —
> the prose only enumerates the two `InvalidBackgroundTimeException` conditions above.
>
> **Observed counter-example:** Garmin's own Notifications sample calls
> `Background.registerForTemporalEvent(new Toybox.Time.Duration(30000))` — a **30-second**
> interval, which is well under the documented 5-minute minimum. Either the 5-minute floor is
> not enforced against a `Duration` in the same way, or the sample is knowingly non-conforming.
> **Do not rely on sub-5-minute polling**; treat the sample as a documentation quirk, not a
> supported cadence.

### 7.3 `requestApplicationWake`

```monkey-c
requestApplicationWake(message as Lang.String) as Void
```

* *"Display a confirmation dialog requesting to launch the application to which the background
  task belongs. If the dialog is confirmed, the application will open. If the dialog is declined,
  the application will not open and the dialog will be dismissed."*
* *"This request is only valid for **widget or device app background tasks**, and will be
  **ignored by watch face apps**."*
* *"`Background.exit()` must be called at some point in the background process after this method
  is invoked because the confirmation dialog will only trigger after the background task exits."*
* Throws `Background.MessageSizeLimitException` — *"Indicates the provided message exceeds the
  size limit (**255 Bytes**). Note that some characters may be larger than 1 Byte."*
* The core topic adds: *"The system may suppress the request if there are not sufficient
  resources to launch the app."*

This is the **Edge 1040 substitute for actionable notifications** — a yes/no prompt, no
per-item action buttons.

### 7.4 `Background.exit` and the data hand-off

```monkey-c
exit(backgroundData as Application.PropertyValueType) as Void
```

* *"Terminates the current background process. All background processes should call this method
  when they have completed the desired tasks. Data passed to this method will either be passed
  immediately to the active application if it is running, or will be saved and passed to the
  application the next time it runs."*
* Allowed data types: `String`, `Number`, `Float`, `Boolean`, `Char`, `Long`, `Double`,
  `Array`, `Dictionary` (arrays/dicts may contain `null` or any listed type). `null` = no data.
* *"This method will exit if called by a background process, but will do nothing if called by the
  main application process."*
* Throws `Background.ExitDataSizeLimitException` — *"Indicates the data provided exceeds the data
  size limit (**approximately 8 KB**). If this exception is caught, the process will not exit and
  should attempt to call `Background.exit()` again with less data."*

### 7.5 The `onBackgroundData` flow

1. Background service runs; calls `Background.exit(data)` with the payload.
2. If the **main app is running**, the payload is delivered **immediately** to
   `AppBase.onBackgroundData(data)`.
3. If the main app is **not** running, the payload is **saved** and delivered the next time the
   app starts — after `onStart()`.
4. `Background.getBackgroundData() as Application.PropertyValueType` retrieves it:
   *"Get data previously saved by a background process. Data is delivered via
   `AppBase.onBackgroundData()`, and is reset to `null` once data has been delivered to the main
   process. **This method always returns `null` in the main application's process.**"*

### 7.6 Lifetime, memory and battery

* **30-second execution limit.** *"Services will also be terminated automatically if they do not
  exit properly within 30 seconds of opening."* — core topic.
* **Severe memory constraint.** *"Background services are allowed to run at any time, including
  while the user is in an activity. In order to achieve this, **the memory pool made available
  to background services is much smaller** than what is available for the application. In many
  instances, the executable code of your application will be larger than the memory pool
  available."*
* **`:background` annotation is mandatory.** Only modules/classes/functions/member variables
  decorated `(:background)` are compiled into the background service. The **Application class
  itself must be marked**, as must the service delegate and anything they reference.
  At `informative` type-check level or above, the compiler errors if background code references
  something not marked `:background`.
* **Background memory limits** (from the Device Reference):

  | Device | Background memory limit |
  |---|---|
  | `edge1040` | **32 768** (32 KB) |
  | `venu441mm` | **65 536** (64 KB) |
  | `venu445mm` | **65 536** (64 KB) |

  → On the Edge 1040 the background service has **32 KB of memory**. A `Communications`
  JSON parse inside a background task on Edge 1040 is tight; keep responses small.

* **Battery vs charging.** Garmin publishes **no** documented policy on background execution
  being restricted to charging. The only documented constraints are the 5-minute temporal
  minimum and the 30-second execution limit. `System.getSystemStats().charging` (API 3.0.0)
  is available for app-level policy. → **UNVERIFIED**, see §11.

---

## 8. Build, signing and sideloading

Sources: <https://developer.garmin.com/connect-iq/core-topics/security/>,
<https://developer.garmin.com/connect-iq/core-topics/build-configuration/>,
<https://developer.garmin.com/connect-iq/core-topics/publishing-to-the-store/>,
SDK `doc/docs/Core_Topics/Debugging.html`, `doc/docs/Connect_IQ_Basics/Your_First_App.html`

### 8.1 Developer key

* *"The Connect IQ compiler requires a developer key be provided for signing when compiling and
  packaging apps. **The required key must be a RSA 4096 bit private key.**"*
* Generate with OpenSSL:

```bash
openssl genrsa -out developer_key.pem 4096
openssl pkcs8 -topk8 -inform PEM -outform DER -in developer_key.pem -out developer_key.der -nocrypt
```

* Pass to the compiler with the **`-y`** option (CLI) — `developer_key.der` is the key file.
* In VS Code: `File > Preferences > Settings > Monkey C` → **`Monkey C: Developer Key Path`**;
  or generate with the **`Monkey C: Generate Developer Key`** command; or let the extension
  create one during **`Monkey C: Verify Installation`**.
* **Keep the key.** *"You will need to use the same key to sign updates to an existing app on the
  store. If you lose your original signing key you will not be able to update your app."*

### 8.2 Signing is mandatory on device

> *"Apps must be signed to run on a Garmin device, and **unsigned apps will be deleted by the
> device**. The Monkey C tool will automatically sign your app based on your key. Your apps will
> run at the **Developer** privilege level. Apps signed by the app store run at the **Trusted**
> privilege level."*

Three trust levels: **Trusted** (store-approved), **Developer** (sideloaded, unsigned-store),
**Untrusted** (must not run on device).

### 8.3 Sideloading

* Build with **`Monkey C: Build for Device`** (VS Code) or `monkeyc` with the `-y` key option.
* Copy the resulting **`*.prg`** into the device's **`GARMIN/APPS/`** directory
  (e.g. `GARMIN/APPS/MYAPP.PRG`), over USB/MTP.
* `System.println()` output goes to **`/GARMIN/APPS/LOGS/<APPNAME>.TXT`**. The log file is
  **not created automatically** — you must create it manually, named to match the `.PRG`
  (`/GARMIN/APPS/LOGS/MYAPP.TXT` for `/GARMIN/APPS/MYAPP.PRG`).
* The device must be in **developer mode** for sideloaded apps to run — **UNVERIFIED** from
  Garmin's public docs (widely documented in the developer community, but not in the pages
  cited above).

### 8.4 Size limits

**Device-level limits (VERIFIED, from `devices.xml` and the Device Reference):**

| Limit | `edge1040` | `venu441mm` | `venu445mm` |
|---|---|---|---|
| `app_storage_capacity` | 10 485 760 (10 MB) | 10 485 760 (10 MB) | 10 485 760 (10 MB) |
| `gfx_resource_pool_size` | 3 145 728 (3 MB) | 4 194 304 (4 MB) | 4 194 304 (4 MB) |
| `max_prg_filespace` | 128 000 000 | 67 108 864 | 67 108 864 |
| `watchdog_count` | 2 500 000 | 240 000 | 240 000 |

**Per-app-type memory limits (VERIFIED):**

| App type | `edge1040` | `venu441mm` | `venu445mm` |
|---|---|---|---|
| Watch App | 1 048 576 | 786 432 | 786 432 |
| Widget | 1 048 576 * | 786 432 | 786 432 |
| Data Field | 131 072 | 262 144 | 262 144 |
| Background | **32 768** | 65 536 | 65 536 |
| Glance | 65 536 | 65 536 | 65 536 |
| Watch Face | **not supported** | 131 072 | 131 072 |
| Audio Content Provider | **not supported** | 524 288 | 524 288 |

\* The Device Reference lists a `Widget` row for `edge1040` at 1 048 576 with the note
*"Requires 4.x SDK"*, but SDK 9.3.0's `devices.xml` does **not** enumerate a separate `widget`
app id for `edge1040` (it lists `background`, `datafield`, `glance`, `watch-app` only). The same
pattern holds for `fenix847mm`, which also shows a `Widget` row on the Device Reference while
`devices.xml` omits the `widget` id — so the omission is a modelling quirk of `devices.xml`
(e.g. `d2air` has watch-app 1 048 576 / widget 524 288 and *does* enumerate `widget`), **not**
evidence that Widget is unsupported on the Edge 1040. Treat the Device Reference as
authoritative for app-type availability.

**Package upload size limit: UNVERIFIED.** No `.iq`/`.prg` package size ceiling is published in
the App Review Guidelines or the SDK documentation. The only hard numbers are the device-level
limits above. A `watchdog_count` of 2 500 000 on the Edge 1040 vs 240 000 on Venu 4 is a
notable difference in allowed execution time.

---

## 9. Device reference tables

Sources: <https://developer.garmin.com/connect-iq/device-reference/edge1040/>,
<https://developer.garmin.com/connect-iq/device-reference/venu441mm/>,
<https://developer.garmin.com/connect-iq/device-reference/venu445mm/> (and the SDK-local mirrors
`doc/docs/Device_Reference/*.html`) — **VERIFIED**

### 9.1 Attributes

| Attribute | `edge1040` | `venu441mm` | `venu445mm` |
|---|---|---|---|
| Screen shape | rectangle | round | round |
| Screen size | **282 x 470** | **390 x 390** | **454 x 454** |
| Display colors | 65 536 | 65 536 | 65 536 |
| **Touch** | **True** | **True** | **True** |
| Buttons | **start, lap** | **enter, esc** | **enter, esc** |
| Launcher icon size | 40 x 40 | 54 x 54 | 65 x 65 |
| Display type (`devices.xml`) | `lcd` | `amoled` | `amoled` |
| PPI (`devices.xml`) | 156 | 326 | 326 |
| BPP (`devices.xml`) | 16 | 16 | 16 |
| `hardwarePartNumber` | 010-02503-00 | 010-03013-02 | 010-03014-00 |
| Solar support | **yes** (`has_solar_support="true"`) | no | no |
| `wifi_exclusions` | `fit_recording="true"` | `normal="true"` | `normal="true"` |

**All three devices have a touch screen.** Note the Edge 1040's button set is
**`start, lap`** — *not* `enter`/`esc` — so any UI code that assumes a "select" button must be
written per-device.

### 9.2 Toast vs notification rendering geometry (`devices.xml`)

| Device | `<toast>` | `<notification>` |
|---|---|---|
| `edge1040` | `x="7" y="7" w="264" h="55" type="partial"` | *(absent)* |
| `venu441mm` | `type="background"` `image="notification_banner.png"` | `y_padding="31" type="fullscreen" mode="preview" show_icon="true" show_subtitle="false"` |
| `venu445mm` | `type="background"` `image="notification_banner.png"` | `y_padding="32" type="fullscreen" mode="preview" show_icon="true" show_subtitle="false"` |

The Edge 1040's toast is a **partial** overlay (264x55 at 7,7) — a compact banner, consistent
with a transflective LCD and no notification system.

### 9.3 Fonts

`edge1040` uses **DejaVu Sans Medium Condensed B** for `FONT_XTINY`–`FONT_LARGE` (13/17/19/22/36)
and **Garmin Robo Units** for the numeric fonts (42/48/64/80), plus Roboto 22/26 for glances.
`venu441mm` uses **Roboto** (30/35/45/53/61) with **Yantramanav** numerics
(97/130/148/179); `venu445mm` uses **Roboto** (37/47/53/61/71) with **Yantramanav** numerics
(112/152/171/209) and additionally exposes Bionic/Rajdhani, Noto Sans SC/TC, MotoyaLCedar,
Noto Naskh, Noto Armenian/Hebrew, Pridi and Kosugi as scalable families.

**Design impact:** the Venu 4's numeric fonts are *much* larger relative to the screen than the
Edge 1040's — the same layout will not fit across both. Use separate resource qualifiers
(`resources-round`, `resources-rectangle-282x470`).

---

## 10. Design implications for the HA bridge app

Target: a CIQ watch app in `watch/`, talking to the FastAPI bridge in `bridge/`.

### 10.1 Manifest

```xml
<?xml version="1.0"?>
<iq:manifest version="3" xmlns:iq="http://www.garmin.com/xml/connectiq">
    <iq:application id="<uuid>" type="watch-app" name="@Strings.appName"
                    entry="GarminHAApp" launcherIcon="@Drawables.launcherIcon" minApiLevel="6.0.0">
        <iq:products>
            <iq:product id="venu441mm"/>
            <iq:product id="venu445mm"/>
            <iq:product id="edge1040"/>
        </iq:products>
        <iq:permissions>
            <iq:uses-permission id="Communications"/>
            <iq:uses-permission id="Background"/>
            <iq:uses-permission id="Notifications"/>
        </iq:permissions>
        <iq:languages/>
        <iq:barrels/>
    </iq:application>
</iq:manifest>
```

* `minApiLevel="6.0.0"` — all three targets are API 6.0. Only major.minor matter, so `6.0` is
  equivalent.
* `Communications` ⇒ `Toybox.Communications` + `Toybox.Authentication`.
  Footnote 1 on the permissions table: *"Communication requires the background permission to be
  enabled, but Authentication does not"* → **also declare `Background`**.
* `Notifications` is required for `Toybox.Notifications`; harmless on the Edge 1040.

### 10.2 Feature detection at runtime

**There is no runtime product-ID API in Connect IQ.** Verified: `productId` does not appear
anywhere in the SDK API metadata (`bin/api.mir` — 0 hits); there is no `System.getDeviceInfo()`,
no `System.DeviceInfo` and no `Application.getAppInfo()` / `Application.AppInfo`. Do not write
code that assumes one.

The correct discriminator is **`System.getDeviceSettings()`** →
<https://developer.garmin.com/connect-iq/api-docs/Toybox/System/DeviceSettings.html>

Relevant `System.DeviceSettings` members (API 1.0.0 unless noted):

| Member | Type | Use here |
|---|---|---|
| `screenWidth` | `Lang.Number` | **282** (Edge 1040), **390** (Venu 4 41mm), **454** (Venu 4 45mm) |
| `screenHeight` | `Lang.Number` | **470** (Edge 1040), **390**, **454** |
| `screenShape` | `System.ScreenShape` | `SCREEN_SHAPE_ROUND`=1, `_SEMI_ROUND`=2, `_RECTANGLE`=3, `_SEMI_OCTAGON`=4 (3.3.0) |
| `isTouchScreen` | `Lang.Boolean` | `true` on all three targets |
| `partNumber` | `Lang.String` | hardware PN — *not* a clean product discriminator (both `venu445mm` and `edge1040` have two PNs) |
| `monkeyVersion` | `[Lang.Number, Lang.Number, Lang.Number]` | device CIQ version |
| `firmwareVersion` | `[Lang.Number, Lang.Number]` | |
| `notificationCount` | `Lang.Number` | active notifications |
| `inputButtons` | `System.ButtonInputs` | bitmask incl. `BUTTON_INPUT_LAP`=0x200, `BUTTON_INPUT_START`=0x40000 |
| `connectionAvailable` / `connectionInfo` / `phoneConnected` | | link status for the BLE proxy |
| `fontScale` | `Lang.Float` | text scaling |

```monkey-c
import Toybox.System;

function isEdge10xx() as Boolean {
    var s = System.getDeviceSettings();
    return s.screenWidth == 282 && s.screenHeight == 470;
}
```

`screenWidth`/`screenHeight` cleanly separates `282x470` (Edge 1040) from `390x390` (Venu 4 41mm)
and `454x454` (Venu 4 45mm) — which is exactly the split between "no `Toybox.Notifications`" and
"has `Toybox.Notifications`" in this target set.

> `Toybox.Has` (e.g. `Has.Comms`, `Has.Notifications`) reflects **API-level** availability.
> Because the Edge 1040's `Notifications` exclusion is a **device-level** restriction, `Has` may
> still report `true` there. Whether Garmin's `Has` module is device-aware is **UNVERIFIED** —
> do not rely on it; use `screenWidth`/`screenHeight` plus a try/catch.

### 10.3 Alerting strategy per device

The bridge already models the watch notification as a **queue + ack** flow
(`GET /v1/notifications`, `POST /v1/notifications/{id}/ack`), which maps cleanly onto the CIQ
notification model.

| Device | Mechanism | Actions? |
|---|---|---|
| Venu 4 41/45 | `Notifications.showNotification(title, subTitle, { :body, :actions, :data })` | **Yes** — user picks an action → `registerForNotificationMessages` fires with `type == NOTIFICATION_MESSAGE_TYPE_SELECTED` and `action == <action's :data>` |
| Edge 1040 | `WatchUi.showToast(text, { :icon })` | **No** — display only; the user cannot pick an action on-watch |
| Edge 1040 (escalation) | `Background.requestApplicationWake("...")` from a background service | Yes/No confirm dialog, 255-byte message limit |

End-to-end flow for a Venu 4:

1. Background service polls `GET /v1/notifications?since=<cursor>` → `NotificationList`
   (`ts`, `cursor`, `n[]` of `WatchNotification` with `id`, `title`, `body`, `priority`,
   `actions[{id,label}]`, `entity_id`, `ack`).
2. For each pending notification, the service calls
   `Notifications.showNotification(n.title, n.body, { :actions => n.actions, :data => n.id })`
   — mapping each `NotificationAction` (`{id, label}`) to a CIQ `Action`
   (`{ :label => label, :data => id }`).
3. The user taps an action on the watch → the foreground app's
   `registerForNotificationMessages` callback fires with `message.action == <the action id>`.
4. The app POSTs `POST /v1/notifications/{id}/ack` with `{"action": "<action id>"}`
   (`NotificationAck.action`) → the bridge fires a `garmin_homeassistant_watch_action` Home Assistant event
   and marks the notification acknowledged.
5. If the user dismisses instead, `message.type == NOTIFICATION_MESSAGE_TYPE_DISMISSED` → ack
   with `{"action": null}`.

For the Edge 1040, steps 2–4 degrade to: `WatchUi.showToast(n.title)` for display, and an
optional explicit ack (no action chosen) — there is no on-watch action affordance.

### 10.4 Transport

Use `Communications.makeWebRequest` with `https://`, `:responseType =>
HTTP_RESPONSE_CONTENT_TYPE_JSON`, and `:headers` carrying
`"Authorization" => "Bearer <watch_token>"` plus the bridge's `X-Garmin-Watch-Id` header.
The bridge accepts either the bridge token or the per-watch token
(`GARMIN_WATCH_TOKENS` maps `watch_id -> token`).

Relevant endpoints (all under `bridge/src/garmin_bridge/app.py`):

| Endpoint | Purpose | CIQ notes |
|---|---|---|
| `GET /v1/health` | connectivity check | **Unauthenticated** — use it for a cheap "is the bridge reachable" probe |
| `GET /v1/config` | watch configuration | `WatchConfig` — see below |
| `GET /v1/entities?since=<rev>&ids=<csv>&verbose=false` | entity snapshot | `EntitySnapshot` (`ts`, `rev`, `areas`, `e[]`); `e[]` are `CompactEntity` (`i`, `n`, `d`, `s`, `f`, `a`) — deliberately compact |
| `GET /v1/entities/{entity_id}` | one entity | `CompactEntity` |
| `POST /v1/commands` | run an HA service | body `{cmd, entity_id, data}` → `CommandResponse` |
| `GET /v1/notifications?since=<cursor>` | queued notifications | `NotificationList` (`ts`, `cursor`, `n[]`) |
| `POST /v1/notifications/{id}/ack` | acknowledge + forward the action | body `{"action": "<id>"}` → fires `garmin_homeassistant_watch_action` in HA |
| `POST /v1/events` | telemetry / button press | body `{type: "telemetry"\|"button"\|"ping"\|"error", ...}` → fires `garmin_watch_button` in HA |

**Delta fetching is already supported.** `GET /v1/entities?since=<rev>` returns only entities
changed after that revision, and `GET /v1/notifications?since=<cursor>` returns only pending
notifications. The watch should persist `rev` / `cursor` locally (e.g. in
`Application.Properties`) and pass the last value on each poll — this is the primary defence
against `NETWORK_RESPONSE_TOO_LARGE` (-402), whose byte threshold is **unpublished**.

`GET /v1/entities` defaults to the compact representation; `verbose=true` returns the full
entity list and **must not** be used over the BLE proxy on a busy HA instance.

`POST /v1/commands` and `POST /v1/events` need a request body — use
`:method => Communications.HTTP_REQUEST_METHOD_POST` with `:body` (API 6.0.3+) and
`"Content-Type" => "application/json"` in `:headers`. On API < 6.0.3 there is no `:body`
option, so those calls must fall back to `application/x-www-form-urlencoded` with the
parameters dictionary.

### 10.4.1 `GET /v1/config` — the server-driven poll contract

`WatchConfig` (`bridge/src/garmin_bridge/models.py`) already encodes the CIQ constraints:

| Field | Default | CIQ implication |
|---|---|---|
| `poll_interval` | `15` (s) | foreground poll cadence — no CIQ limit applies to the foreground process, but each poll is a BLE round-trip, so keep it modest |
| `background_interval` | `900` (s = **15 min**) | **Deliberately above the CIQ 5-minute `registerForTemporalEvent` minimum** (§7.2). The watch must clamp this to ≥ 300 s or `Background.InvalidBackgroundTimeException` is thrown |
| `page_size` | `25` | max entities per request — the server-side bound on response size, and the main mitigation for `NETWORK_RESPONSE_TOO_LARGE` (-402) |
| `message` | `""` | optional server-side notice for the watch home screen |

**Action item for the watch app:** fetch `/v1/config` once at startup, persist it (e.g. in
`Application.Properties`), and enforce `max(background_interval, 300)` before calling
`Background.registerForTemporalEvent`. Do not hard-code 15 minutes — the server may change it,
but it can never legally go below 5 minutes on CIQ.

### 10.5 Background polling

`Background.registerForTemporalEvent(new Time.Duration(5 * 60))` is the documented minimum
cadence — **5 minutes is the fastest legal poll**. Respect
`Background.InvalidBackgroundTimeException` (schedule ≥ 5 min after
`Background.getLastTemporalEventTime()`), and remember the **30-second** execution limit and the
**32 KB** background memory pool on the Edge 1040. Do the network call *inside* the background
service, then `Background.exit(payload)` with a ≤ ~8 KB payload, and deliver to the UI via
`AppBase.onBackgroundData()`.

The bridge's `WatchConfig.background_interval` (default 900 s) should drive this, clamped to
≥ 300 s (§10.4.1). Use the `Time.Moment` form when you need an absolute next-poll time
(`Background.getLastTemporalEventTime().add(new Time.Duration(300))`), because a `Time.Duration`
interval must itself be ≥ 5 minutes.

**Payload discipline on the Edge 1040.** With a 32 KB background pool and a ~8 KB
`Background.exit()` payload cap, do **not** copy the entity snapshot into the background
payload. Have the background service POST a small "there is new data" marker (e.g. the new
`rev`) and let the **foreground** app fetch the delta. The background service's job is to
detect change and to raise the notification, not to transport the state.

### 10.6 Resources

Round vs rectangle need separate resource trees:
`resources-round` (390x390 and 454x454 differ in size — use `resources-round-390x390` and
`resources-round-454x454`) and `resources-rectangle-282x470`. Family qualifiers:
`resources-round` / `resources-rectangle` are the screen-shape qualifiers; the size suffix
narrows it further (per the Build Configuration core topic). Device qualifiers
(`resources-venu441mm`) take precedence over family qualifiers and **cannot be combined** with
family qualifiers in the same folder name.

The Edge 1040's button set is **`start, lap`** (not `enter`/`esc`), and its fonts are much
smaller relative to the screen than the Venu 4's (DejaVu Sans Condensed vs Roboto/Yantramanav,
§9.3) — a single layout will not work across both without separate resource trees.

---

## 11. UNVERIFIED items

Explicitly flagged — **do not treat these as facts**:

| # | Item | Status |
|---|---|---|
| 1 | **Byte threshold for `BLE_REQUEST_TOO_LARGE` (-102)** (serialised request size limit over the BLE proxy) | **UNVERIFIED.** Not published in Garmin's docs or the SDK. Only the error description exists. |
| 2 | **Byte threshold for `NETWORK_RESPONSE_TOO_LARGE` (-402)** | **UNVERIFIED.** Same. |
| 3 | **Battery-vs-charging policy for background execution** | **UNVERIFIED.** Only the 5-minute temporal minimum and the 30-second execution limit are documented. `System.getSystemStats().charging` (API 3.0.0) is available for app-level logic. |
| 4 | **`.iq` / `.prg` package upload size limit** | **UNVERIFIED.** Not in the App Review Guidelines or SDK docs. Only device-level limits (10 MB app storage, 3–4 MB gfx pool, per-app-type memory limits, `max_prg_filespace`) are known. |
| 5 | **Whether `:mediaEncoding` is accepted by `makeWebRequest`** | **UNVERIFIED.** Documented in the parameter prose but **absent from the `options` typedef**. |
| 6 | **Whether `Toybox.Has.Notifications` is `false` on the Edge 1040** | **UNVERIFIED.** The `Toybox.Has` module was not analysed in this pass; it may be device-aware or purely API-level. **There is no runtime product-ID API at all** (no `productId`, `System.getDeviceInfo()`, or `Application.getAppInfo()` in `bin/api.mir`), so use `System.getDeviceSettings().screenWidth/screenHeight` plus try/catch. |
| 7 | **The exact interaction of the `Time.Moment` form with the 5-minute temporal restriction** | **UNVERIFIED.** The exception prose lists two conditions; the Moment-vs-Duration nuance is inferred, not documented. |
| 8 | **Semantics of the `wifi_exclusions` flags** (`normal="true"` on Venu 4, `fit_recording="true"` on Edge 1040) | **UNVERIFIED.** The XML attributes are read verbatim from `devices.xml`; their runtime meaning is not documented. |
| 9 | **Device "developer mode" prerequisite for sideloaded apps** | **UNVERIFIED** from Garmin's published pages cited here. |
| 10 | **Whether the "Notifications" permission produces a user-facing install prompt** | **UNVERIFIED.** The permission is absent from the published permission table but required by the module page and used by Garmin's own sample manifest. |
| 11 | **Exact user-facing presentation of the Edge 1040 toast** | **UNVERIFIED.** Geometry is known from `devices.xml` (`partial`, 264x55) but the rendered result is not documented. |
| 12 | **`System.getSystemStats().solarIntensity` on the Edge 1040 Solar** | **UNVERIFIED.** The member exists (API 3.2.0) and the device declares `has_solar_support="true"`, but no per-device support list is published for `Stats` members. |
| 13 | **`System.getDeviceSettings().partNumber` value at runtime** | **UNVERIFIED.** The API exposes `partNumber as Lang.String`, but Garmin does not document whether it returns the CIQ part number (`006-B3843-00`) or the hardware part number (`010-02503-00`) — the two differ for every device. |

---

## 12. Documentation gaps worth noting

* **SDK 9.3.0's `devices.xml` lacks Edge 1060, Edge Explore 3 and Edge Explore 3 Plus**, which
  *do* appear in the online Doxygen supported-device lists (e.g. `Edge® 1060` appears in the
  Communications module list). The SDK device DB is therefore **not** a complete device list —
  always prefer the online Doxygen lists for *support* questions and `devices.xml` for
  *device-capability and limit* questions.
* **`Toybox.Notifications` support is device-gated, not merely API-level-gated.** The Edge 1040
  is API 6.0 yet excluded — the single most important trap in this report.
* Garmin's own documentation is internally inconsistent about the `Notifications` permission
  (§3.4). Treat the module page + the official sample manifest as authoritative.

---

## Appendix A — source URL index

**API reference (Doxygen)**

* <https://developer.garmin.com/connect-iq/api-docs/Toybox/Communications.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/Background.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/WatchUi.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/Attention.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/Sensor.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/System.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/UserProfile.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/PersistedContent.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/System/DeviceSettings.html>
* <https://developer.garmin.com/connect-iq/api-docs/Toybox/System/Stats.html>

**Core topics**

* <https://developer.garmin.com/connect-iq/core-topics/notifications/>
* <https://developer.garmin.com/connect-iq/core-topics/backgrounding/>
* <https://developer.garmin.com/connect-iq/core-topics/https/>
* <https://developer.garmin.com/connect-iq/core-topics/security/>
* <https://developer.garmin.com/connect-iq/core-topics/manifest-and-permissions/>
* <https://developer.garmin.com/connect-iq/core-topics/build-configuration/>
* <https://developer.garmin.com/connect-iq/core-topics/communicating-with-mobile-apps/>
* <https://developer.garmin.com/connect-iq/core-topics/authenticated-web-services/>
* <https://developer.garmin.com/connect-iq/core-topics/downloading-content/>
* <https://developer.garmin.com/connect-iq/core-topics/intents/>
* <https://developer.garmin.com/connect-iq/core-topics/getting-the-users-attention/>
* <https://developer.garmin.com/connect-iq/core-topics/publishing-to-the-store/>

**Devices**

* <https://developer.garmin.com/connect-iq/compatible-devices/>
* <https://developer.garmin.com/connect-iq/device-reference/edge1040/>
* <https://developer.garmin.com/connect-iq/device-reference/venu441mm/>
* <https://developer.garmin.com/connect-iq/device-reference/venu445mm/>

**SDK**

* <https://developer.garmin.com/downloads/connect-iq/sdks/sdks.json>
* `https://developer.garmin.com/downloads/connect-iq/sdks/connectiq-sdk-lin-9.3.0-2026-10-20-95888f262.zip`

**SDK-local paths (from the 9.3.0 archive)**

* `bin/version.txt`, `bin/compilerInfo.xml` — SDK version
* `bin/api.mir`, `bin/api.db` — API metadata (per-symbol `minSdk`)
* `mb/com/garmin/monkeybrains/devices/devices.xml` — device database
* `doc/docs/Device_Reference/{edge1040,venu441mm,venu445mm}.html` — device reference mirrors
* `doc/docs/Core_Topics/*.html` — core-topic mirrors
* `samples/WebRequest/`, `samples/Notifications/` — reference implementations

**Project paths referenced in §10**

* `bridge/src/garmin_bridge/app.py` — routes, auth (`require_any` / `require_admin`),
  `WATCH_ID_HEADER = "X-Garmin-Watch-Id"`
* `bridge/src/garmin_bridge/models.py` — `EntitySnapshot`, `CompactEntity`, `WatchConfig`,
  `NotificationList`, `WatchNotification`, `NotificationAck`, `CommandRequest`, `WatchEvent`
* `bridge/src/garmin_bridge/config.py` — `HA_TOKEN`, `GARMIN_BRIDGE_TOKEN`, `GARMIN_WATCH_TOKEN`,
  `GARMIN_WATCH_TOKENS`, `GARMIN_BRIDGE_PORT` (default 8099)

