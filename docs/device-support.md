# Device support

Garmin Home Assistant is built for two watches: the **Venu 4** and the
**Edge 1040 / Edge 1040 Solar**.  They run the same Connect IQ API level,
but they do not implement the same set of modules, so the application
behaves slightly differently on them.

> Garmin sells the solar variant of the Edge 1040 as the *Edge 1040 Solar*.
> The Connect IQ compatible device list has no *Forerunner 1040*, so the Edge
> 1040 is the only device of that family this project supports.

## The summary

| | Venu 4 41 mm | Venu 4 45 mm | Edge 1040 / Edge 1040 Solar |
| --- | --- | --- | --- |
| Product id | `venu441mm` | `venu445mm` | `edge1040` |
| Connect IQ API level | 6.0 | 6.0 | 6.0 |
| Resolution | 390 × 390 | 454 × 454 | 282 × 470 |
| Shape | round | round | rectangle |
| `Toybox.Communications` | yes | yes | yes |
| `Toybox.Notifications` | **yes** | **yes** | **no** |
| `Toybox.Background` | yes | yes | yes, but 32 KB |
| Notifications with buttons | yes | yes | no, toast only |
| Build | `watch/build.sh venu` | `watch/build.sh venu` | `watch/build.sh edge` |

The full, sourced list of every module and every function of the two
devices is in
[`ciq-device-capabilities.md`](ciq-device-capabilities.md).  That document
is the reference; this page is the summary.

## What the difference means in practice

### The notification presenter

The Venu 4 implements `Toybox.Notifications`, so the application can raise a
system notification with buttons.  The user picks a button without opening
the application.

The Edge 1040 does not implement the module at all.  That is a device
restriction and not an API level restriction: the Edge 1040 runs Connect IQ
6.0, which is well above the 5.1.0 that `Toybox.Notifications` needs, but
the device is excluded from the supported list of the module.  The
application therefore asks the user to open the application with
`Background.requestApplicationWake()` and shows the notification in its
inbox.

The build reflects that:

| Build | Presenter | Manifest |
| --- | --- | --- |
| Venu | `watch/variants/notifications/NotificationPresenter.mc` | `watch/manifest.xml`, with the `Notifications` permission |
| Edge | `watch/variants/toast/NotificationPresenter.mc` | `watch/manifest-edge.xml`, without it |

Everything else is shared, so the two devices cannot drift apart.  The
static check in `scripts/check_ciq.py` makes sure that the shared sources
never use `Toybox.Notifications` and that only the Venu variant does.

### The memory of a background service

The Edge 1040 offers only 32 KB for a background service.  The base build
therefore does not keep a background service alive; the background delegate
only refreshes the notification queue, and everything else happens while
the application is in the foreground.

The `Background` permission is still declared, because
`Toybox.Communications` requires it.

### The runtime detection

The application does not guess.  `watch/source/Capabilities.mc` asks the
device with `Toybox.System.getDeviceSettings()` and stores the answer, so a
device that is added to the manifest later works without a new build.

## Other devices

The application is written against the API level 6.0 and the modules that
the two devices implement.  Other API level 6.0 devices will very likely
work, but they are not tested and they are not in the manifest, so the
store does not offer the application for them.

The one thing that would have to change for another device is the
notification presenter, if the device implements `Toybox.Notifications` and
the Edge presenter is used for it.  Adding a device means:

1. adding its product id to the manifest,
2. adding a presenter under `watch/variants/` when the device needs a
   different one,
3. adding a jungle file for the build,
4. adding the device to `scripts/check_ciq.py`, so that the static check
   knows about it.

## Honest limitations

* The watch application is **not compiled** by the open source CI
  pipeline, because the Connect IQ SDK is proprietary and cannot be
  redistributed.  The pipeline runs a static check of the sources instead.
  See [`development.md`](development.md).
* The device capabilities are documented from the Connect IQ API
  documentation and from the device database of the SDK.  The application
  degrades gracefully when a module is missing, so a wrong assumption
  shows up as a missing feature and not as a crash.
* A self signed certificate for the bridge is not accepted by the Connect IQ
  runtime.  Use a certificate from a public authority or plain HTTP on a
  network you trust.
