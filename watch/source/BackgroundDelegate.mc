//
// The background service.
//
// The service is woken by a temporal event (the shortest interval the
// Connect IQ runtime allows is five minutes, see
// https://developer.garmin.com/connect-iq/articles/core-topics/Backgrounding.html),
// asks the bridge for the notifications that are still pending and raises
// them on the watch.
//
// The service runs with a very small memory pool -- 32 KB on the Edge 1040
// and 64 KB on the Venu 4 -- so it does as little as possible: one request,
// no entity list and no user interface.  The payload that is handed back to
// the foreground app with Background.exit() only carries the number of
// notifications that were found, never the notifications themselves.
//
// A notification is only raised once.  The bridge keeps a notification in
// the queue until it is acknowledged, so the service remembers the number
// of the newest notification it has already shown.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Background;
import Toybox.Lang;
import Toybox.System;

(:background)
class BackgroundDelegate extends System.ServiceDelegate {

    private var mClient as BridgeClient;

    function initialize() {
        System.ServiceDelegate.initialize();
        mClient = new BridgeClient(
            Settings.bridgeUrl(),
            Settings.token(),
            Settings.watchId()
        );
    }

    //! Called when the temporal event fires.
    function onTemporalEvent() as Void {
        if (Settings.bridgeUrl() == "") {
            // Nothing to poll; do not burn a background slot.
            Background.exit(null);
            return;
        }
        mClient.fetchNotifications(Settings.notificationCursor(), method(:onNotifications));
    }

    //! The bridge answered (or did not).
    function onNotifications(code as Lang.Number, data as Lang.Dictionary?) as Void {
        var raised = 0;
        if (code == 200 && data != null) {
            raised = _raise(data);
            Settings.setNotificationCursor(_cursor(data));
            Settings.setPendingNotifications(raised);
        }
        // The foreground app only needs to know that something changed.
        Background.exit({ "n" => raised });
    }

    //! Show every pending notification and return how many were raised.
    private function _raise(data as Lang.Dictionary) as Lang.Number {
        var rows = Values.array(Values.member(data, "n"));
        if (rows == null) {
            return 0;
        }
        var raised = 0;
        var until = Settings.raisedUntil();
        var highest = until;
        var actionable = false;
        for (var i = 0; i < rows.size(); i++) {
            var row = rows[i] as Lang.Array;
            if (row == null) {
                continue;
            }
            var title = Values.string(row[EntityStore.NOTIF_TITLE]);
            var body = Values.string(row[EntityStore.NOTIF_BODY]);
            var id = Values.string(row[EntityStore.NOTIF_ID]);
            var actions = Values.array(row[EntityStore.NOTIF_ACTIONS]);
            if (id == null) {
                id = "";
            }
            var counter = _counter(id);
            if (counter >= 0 && counter <= until) {
                // This notification was raised by an earlier run.
                continue;
            }
            if (title == null || title == "") {
                title = "Home Assistant";
            }
            NotificationPresenter.show(title, body, actions, id);
            raised++;
            if (actions != null && actions.size() > 0) {
                actionable = true;
            }
            if (counter > highest) {
                highest = counter;
            }
        }
        Settings.setRaisedUntil(highest);
        if (raised > 0 && actionable && NotificationPresenter.supportsWakeRequest()) {
            // The toast cannot carry the actions, so ask the user to open
            // the app where the actions are offered.
            NotificationPresenter.wake("Home Assistant: open for actions");
        }
        return raised;
    }

    //! The cursor of the notification queue.
    private function _cursor(data as Lang.Dictionary) as Lang.Number {
        var cursor = Values.number(Values.member(data, "cursor"));
        return cursor == null ? Settings.notificationCursor() : cursor;
    }

    //! The number behind a notification id.
    //!
    //! The bridge hands out the ids "n1", "n2", ... so the counter behind
    //! the id is enough to remember what was already shown.  An id that does
    //! not follow that pattern yields -1, which disables the check.
    private function _counter(notificationId as Lang.String) as Lang.Number {
        if (notificationId == null || notificationId.length() < 2) {
            return -1;
        }
        if (notificationId.substring(0, 1) != "n") {
            return -1;
        }
        var digits = notificationId.substring(1, notificationId.length());
        var value = 0;
        // Lang.String has no charAt(); toCharArray() is the documented way
        // to look at the code points of a string.
        var chars = digits.toCharArray();
        for (var i = 0; i < chars.size(); i++) {
            var character = chars[i] as Lang.Char;
            if (character == null) {
                return -1;
            }
            var code = character.toNumber();
            if (code < 48 || code > 57) {
                return -1;
            }
            value = value * 10 + (code - 48);
        }
        return value;
    }
}
