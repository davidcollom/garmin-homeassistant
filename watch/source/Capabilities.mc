//
// Runtime capability detection.
//
// Connect IQ has no runtime product id API, so the app works out what it
// can do from Toybox.System.getDeviceSettings().  The relevant members are
// documented at
// https://developer.garmin.com/connect-iq/api-docs/Toybox/System/DeviceSettings.html
//
// The screen geometry separates the two target families:
//
//     282 x 470   Edge 1040 / Edge 1040 Solar  (rectangular)
//     390 x 390   Venu 4 41 mm                 (round)
//     454 x 454   Venu 4 45 mm                 (round)
//
// The Edge 1040 does not implement Toybox.Notifications at all.  Which
// presenter is used is decided at build time (variants/notifications for
// the Venu, variants/toast for the Edge), so the capability report below
// asks the presenter itself instead of guessing from the geometry.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;
import Toybox.System;

(:background)
class Capabilities {

    // Screen geometry of the supported devices.
    static const EDGE_1040_WIDTH as Lang.Number = 282;
    static const EDGE_1040_HEIGHT as Lang.Number = 470;
    static const VENU_4_41_WIDTH as Lang.Number = 390;
    static const VENU_4_45_WIDTH as Lang.Number = 454;

    // Connect IQ API level of the supported devices, encoded as
    // major * 100 + minor.
    static const API_LEVEL_6_0 as Lang.Number = 600;

    private var mWidth as Lang.Number = 0;
    private var mHeight as Lang.Number = 0;
    private var mShape as Lang.Number = System.SCREEN_SHAPE_RECTANGLE;
    private var mTouch as Lang.Boolean = false;
    private var mApiLevel as Lang.Number = 0;
    private var mPhoneConnected as Lang.Boolean = false;
    private var mConnectionAvailable as Lang.Boolean = false;
    private var mButtons as Lang.Number = 0;
    private var mBattery as Lang.Number = -1;
    private var mCharging as Lang.Boolean = false;
    private var mMemoryUsed as Lang.Number = 0;
    private var mMemoryTotal as Lang.Number = 0;
    private var mMemoryFree as Lang.Number = 0;
    private var mFontScale as Lang.Number = 1;

    function initialize() {
        refresh();
    }

    //! Refresh everything that can change while the app is running.
    function refresh() as Void {
        try {
            var settings = System.getDeviceSettings();
            if (settings != null) {
                mWidth = settings.screenWidth;
                mHeight = settings.screenHeight;
                mShape = settings.screenShape;
                mTouch = settings.isTouchScreen;
                mPhoneConnected = settings.phoneConnected;
                mConnectionAvailable = settings.connectionAvailable;
                mButtons = settings.inputButtons;
                mFontScale = settings.fontScale;
                var version = settings.monkeyVersion;
                if (version != null && version.size() > 1) {
                    mApiLevel = version[0] * 100 + version[1];
                }
            }
        } catch (e) {
            // Keep the defaults, the app still works without them.
        }
        try {
            var stats = System.getSystemStats();
            if (stats != null) {
                mBattery = stats.battery;
                mMemoryUsed = stats.usedMemory;
                mMemoryTotal = stats.totalMemory;
                mMemoryFree = stats.freeMemory;
                mCharging = stats.charging;
            }
        } catch (e) {
            mBattery = -1;
        }
    }

    function width() as Lang.Number {
        return mWidth;
    }

    function height() as Lang.Number {
        return mHeight;
    }

    function shape() as Lang.Number {
        return mShape;
    }

    //! True for the round Venu 4 displays.
    function isRound() as Lang.Boolean {
        return mShape == System.SCREEN_SHAPE_ROUND;
    }

    function hasTouch() as Lang.Boolean {
        return mTouch;
    }

    //! Connect IQ version encoded as major * 100 + minor, e.g. 600 for 6.0.
    function apiLevel() as Lang.Number {
        return mApiLevel;
    }

    //! True when the phone is reachable, which is what the Bluetooth proxy
    //! needs to reach the bridge.
    function phoneConnected() as Lang.Boolean {
        return mPhoneConnected;
    }

    //! True when any communication channel is available.
    function connectionAvailable() as Lang.Boolean {
        return mConnectionAvailable;
    }

    //! The physical buttons of the device as a bit mask.
    function inputButtons() as Lang.Number {
        return mButtons;
    }

    //! True when the device has a button that behaves like "select".
    function hasSelectButton() as Lang.Boolean {
        return (mButtons & System.BUTTON_INPUT_SELECT) != 0 ||
               (mButtons & System.BUTTON_INPUT_START) != 0;
    }

    //! True when the device has a button that behaves like "back".
    function hasBackButton() as Lang.Boolean {
        return (mButtons & System.BUTTON_INPUT_ESC) != 0 ||
               (mButtons & System.BUTTON_INPUT_LAP) != 0;
    }

    //! Battery percentage or -1 when it cannot be determined.
    function battery() as Lang.Number {
        return mBattery;
    }

    function charging() as Lang.Boolean {
        return mCharging;
    }

    function memoryUsed() as Lang.Number {
        return mMemoryUsed;
    }

    function memoryTotal() as Lang.Number {
        return mMemoryTotal;
    }

    function memoryFree() as Lang.Number {
        return mMemoryFree;
    }

    function fontScale() as Lang.Number {
        return mFontScale;
    }

    //! True for the Edge 1040 family, which has no Toybox.Notifications.
    function isEdge1040() as Lang.Boolean {
        return mWidth == EDGE_1040_WIDTH && mHeight == EDGE_1040_HEIGHT;
    }

    //! A best effort product name.
    //!
    //! Connect IQ does not expose a product id at runtime, so the name is
    //! derived from the screen geometry.  It is only used as a hint for the
    //! user in the bridge administration page.
    function model() as Lang.String {
        if (isEdge1040()) {
            return "edge1040";
        }
        if (mWidth == VENU_4_45_WIDTH) {
            return "venu445mm";
        }
        if (mWidth == VENU_4_41_WIDTH) {
            return "venu441mm";
        }
        return "garmin" + mWidth.toString() + "x" + mHeight.toString();
    }

    //! True when the device can raise system notifications with actions.
    //!
    //! The answer comes from the presenter, which is chosen at build time:
    //! the Venu build uses Toybox.Notifications, the Edge build uses a toast.
    function supportsSystemNotifications() as Lang.Boolean {
        return NotificationPresenter.supportsSystemNotifications();
    }

    //! True when the device can ask the user to open the app.
    function supportsWakeRequest() as Lang.Boolean {
        return NotificationPresenter.supportsWakeRequest();
    }

    //! Capabilities that are reported to the bridge when registering.
    function asDictionary() as Lang.Dictionary {
        return {
            "touch" => mTouch,
            "round" => isRound(),
            "battery" => mBattery >= 0,
            "charging" => mCharging,
            "background" => true,
            "notifications" => supportsSystemNotifications(),
            "wake" => supportsWakeRequest(),
            "api" => mApiLevel,
            "screen" => mWidth.toString() + "x" + mHeight.toString()
        };
    }
}
