//
// Settings for the Garmin Home Assistant watch application.
//
// User editable settings are declared in resources/settings/properties.xml
// and are read through Toybox.Application.Properties.  Everything the watch
// has to remember for itself (its id, the device token handed out by the
// bridge, the last known revision) lives in Toybox.Application.Storage.
//
// Both APIs are available in the background service as well, so the
// background delegate can find the bridge and the token without the
// foreground app having to run first.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
using Toybox.Application as App;
import Toybox.Lang;
import Toybox.System;

(:background)
class Settings {

    //! Storage keys.
    static const KEY_WATCH_ID as Lang.String = "watchId";
    static const KEY_DEVICE_TOKEN as Lang.String = "deviceToken";
    static const KEY_REVISION as Lang.String = "revision";
    static const KEY_NOTIFICATION_CURSOR as Lang.String = "notificationCursor";
    static const KEY_PENDING as Lang.String = "pendingNotifications";
    static const KEY_RAISED_UNTIL as Lang.String = "raisedUntil";
    static const KEY_BACKGROUND_INTERVAL as Lang.String = "backgroundInterval";
    static const KEY_PAGE_SIZE as Lang.String = "pageSize";
    static const KEY_SERVER_MESSAGE as Lang.String = "serverMessage";

    //! Property names, see resources/settings/properties.xml.
    static const PROPERTY_URL as Lang.String = "BridgeUrl";
    static const PROPERTY_TOKEN as Lang.String = "BridgeToken";
    static const PROPERTY_POLL_INTERVAL as Lang.String = "PollInterval";
    static const PROPERTY_SHOW_AREAS as Lang.String = "ShowAreas";
    static const PROPERTY_CONFIRM as Lang.String = "ConfirmCommands";

    //! The Connect IQ runtime refuses a temporal background event that is
    //! scheduled less than five minutes out.
    static const MIN_BACKGROUND_INTERVAL as Lang.Number = 300;
    //! Default foreground poll interval in seconds.
    static const DEFAULT_POLL_INTERVAL as Lang.Number = 30;
    //! The shortest foreground poll interval that is worth doing.
    static const MIN_POLL_INTERVAL as Lang.Number = 10;

    private static var mWatchId as Lang.String? = null;
    private static var mDeviceToken as Lang.String? = null;

    //! Base URL of the bridge, for example "http://192.168.1.10:8099".
    static function bridgeUrl() as Lang.String {
        var value = _property(PROPERTY_URL);
        if (value == null) {
            return "";
        }
        return value as Lang.String;
    }

    //! Shared bootstrap token configured by the user.
    static function bootstrapToken() as Lang.String {
        var value = _property(PROPERTY_TOKEN);
        if (value == null) {
            return "";
        }
        return value as Lang.String;
    }

    //! Token the bridge issued for this particular watch.
    static function deviceToken() as Lang.String {
        if (mDeviceToken != null) {
            return mDeviceToken;
        }
        var stored = _storage(KEY_DEVICE_TOKEN);
        mDeviceToken = stored == null ? "" : stored as Lang.String;
        return mDeviceToken;
    }

    //! Remember the per watch token so that only the shared token has to be
    //! configured once.
    static function setDeviceToken(token as Lang.String) as Void {
        mDeviceToken = token;
        App.Storage.setValue(KEY_DEVICE_TOKEN, token);
    }

    //! The token the watch calls the bridge with.  A token that the bridge
    //! issued for this watch takes precedence over the shared bootstrap
    //! token.
    static function token() as Lang.String {
        var token = deviceToken();
        if (token == null || token == "") {
            token = bootstrapToken();
        }
        if (token == null) {
            return "";
        }
        return token;
    }

    //! Seconds between foreground polls.  Zero means "ask the bridge".
    static function pollInterval() as Lang.Number {
        var value = _property(PROPERTY_POLL_INTERVAL);
        if (value == null) {
            return DEFAULT_POLL_INTERVAL;
        }
        var seconds = value as Lang.Number;
        if (seconds == null || seconds < MIN_POLL_INTERVAL) {
            return MIN_POLL_INTERVAL;
        }
        return seconds;
    }

    //! Group the entity list by Home Assistant area.
    static function showAreas() as Lang.Boolean {
        var value = _property(PROPERTY_SHOW_AREAS);
        if (value == null) {
            return true;
        }
        return value as Lang.Boolean;
    }

    //! Ask for a confirmation before running a command.
    static function confirmCommands() as Lang.Boolean {
        var value = _property(PROPERTY_CONFIRM);
        if (value == null) {
            return false;
        }
        return value as Lang.Boolean;
    }

    //! Stable identifier of this watch.
    static function watchId() as Lang.String {
        if (mWatchId != null) {
            return mWatchId;
        }
        var stored = _storage(KEY_WATCH_ID);
        if (stored == null || (stored as Lang.String) == "") {
            stored = _generateId();
            App.Storage.setValue(KEY_WATCH_ID, stored);
        }
        mWatchId = stored as Lang.String;
        return mWatchId;
    }

    //! Revision of the entity list the watch last downloaded.
    static function revision() as Lang.Number {
        var stored = _storage(KEY_REVISION);
        if (stored == null) {
            return 0;
        }
        var value = stored as Lang.Number;
        return value == null ? 0 : value;
    }

    static function setRevision(revision as Lang.Number) as Void {
        App.Storage.setValue(KEY_REVISION, revision);
    }

    //! Cursor of the notification queue the watch last read.
    static function notificationCursor() as Lang.Number {
        var stored = _storage(KEY_NOTIFICATION_CURSOR);
        if (stored == null) {
            return 0;
        }
        var value = stored as Lang.Number;
        return value == null ? 0 : value;
    }

    static function setNotificationCursor(cursor as Lang.Number) as Void {
        App.Storage.setValue(KEY_NOTIFICATION_CURSOR, cursor);
    }

    //! Number of notifications the background service found.
    static function pendingNotifications() as Lang.Number {
        var stored = _storage(KEY_PENDING);
        if (stored == null) {
            return 0;
        }
        var value = stored as Lang.Number;
        return value == null ? 0 : value;
    }

    static function setPendingNotifications(count as Lang.Number) as Void {
        App.Storage.setValue(KEY_PENDING, count);
    }

    //! The number of the newest notification the background service raised.
    //!
    //! The bridge hands out the ids "n1", "n2", ... so the counter behind
    //! the id is enough to remember what was already shown.  The foreground
    //! app uses this to avoid raising the same notification twice.
    static function raisedUntil() as Lang.Number {
        var stored = _storage(KEY_RAISED_UNTIL);
        if (stored == null) {
            return 0;
        }
        var value = stored as Lang.Number;
        if (value == null) {
            return 0;
        }
        return value;
    }

    static function setRaisedUntil(value as Lang.Number) as Void {
        App.Storage.setValue(KEY_RAISED_UNTIL, value == null ? 0 : value);
    }

    //! Seconds between background polls, never below the five minutes that
    //! the Connect IQ runtime insists on.
    static function backgroundInterval() as Lang.Number {
        var stored = _storage(KEY_BACKGROUND_INTERVAL);
        var seconds = MIN_BACKGROUND_INTERVAL;
        if (stored != null) {
            var value = stored as Lang.Number;
            if (value != null && value > seconds) {
                seconds = value;
            }
        }
        return seconds;
    }

    static function setBackgroundInterval(seconds as Lang.Number) as Void {
        var clamped = seconds < MIN_BACKGROUND_INTERVAL ? MIN_BACKGROUND_INTERVAL : seconds;
        App.Storage.setValue(KEY_BACKGROUND_INTERVAL, clamped);
    }

    //! Maximum number of entities the bridge puts into one page.
    static function pageSize() as Lang.Number {
        var stored = _storage(KEY_PAGE_SIZE);
        if (stored == null) {
            return 25;
        }
        var value = stored as Lang.Number;
        if (value == null || value < 1) {
            return 25;
        }
        return value;
    }

    static function setPageSize(size as Lang.Number) as Void {
        App.Storage.setValue(KEY_PAGE_SIZE, size);
    }

    //! An optional notice the bridge wants to show on the watch.
    static function serverMessage() as Lang.String {
        var stored = _storage(KEY_SERVER_MESSAGE);
        if (stored == null) {
            return "";
        }
        return stored as Lang.String;
    }

    static function setServerMessage(message as Lang.String) as Void {
        App.Storage.setValue(KEY_SERVER_MESSAGE, message == null ? "" : message);
    }

    // -- helpers -----------------------------------------------------------

    private static function _property(key as Lang.String) as Lang.Object? {
        try {
            return App.Properties.getValue(key);
        } catch (e) {
            // The property is not defined in properties.xml.
            return null;
        }
    }

    private static function _storage(key as Lang.String) as Lang.Object? {
        try {
            return App.Storage.getValue(key);
        } catch (e) {
            return null;
        }
    }

    //! Build an identifier that is stable for the lifetime of the install.
    private static function _generateId() as Lang.String {
        var seed = 0;
        try {
            seed = System.getTimer();
        } catch (e) {
            seed = 0;
        }
        var id = "ga-" + (seed % 1679616).toString();
        for (var i = 0; i < 3; i++) {
            seed = (seed * 31 + i * 7919) % 2147483647;
            id += "-" + (seed % 1679616).toString();
        }
        return id;
    }
}
