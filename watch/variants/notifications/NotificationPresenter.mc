//
// Notification presenter for the devices that implement
// Toybox.Notifications: the Venu 4 41 mm and the Venu 4 45 mm.
//
// The Edge 1040 does not implement the module at all -- it is excluded
// from the supported device list of
// https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html
// even though it runs Connect IQ 6.0, which is well above the 5.1.0 that
// the module requires.  The Edge build therefore uses
// variants/toast/NotificationPresenter.mc instead, and this file must never
// be part of that build.
//
// The module needs the "Notifications" permission, which is declared in
// manifest.xml.
//
// The action data of a notification is the string
// "<notification id>|<action id>".  A string is used because the
// documentation describes the action data as "a string and serializable
// data"; a dictionary would work as well but the exact shape the runtime
// hands back to AppBase.onStart() is not documented, and a string can be
// parsed the same way in both places.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;
import Toybox.Notifications;

(:background)
class NotificationPresenter {

    //! The user picked one of the actions of the notification.
    static const ACTION_SELECTED as Lang.Number = 1;
    //! The user dismissed the notification without picking an action.
    static const ACTION_DISMISSED as Lang.Number = 0;

    //! The handler that receives the notification messages.
    private static var mHandler as Lang.Method? = null;

    //! True: this build can raise system notifications with actions.
    static function supportsSystemNotifications() as Lang.Boolean {
        return true;
    }

    //! True: this build can ask the user to open the app.
    static function supportsWakeRequest() as Lang.Boolean {
        return false;
    }

    //! Listen for the user interacting with a notification.
    //!
    //! The handler is called with (notificationId, actionId, type).  The
    //! action id is an empty string when the notification was dismissed
    //! without picking an action.
    //!
    //! This may only be called from the foreground; the background service
    //! has no notification message channel.
    static function register(handler as Lang.Method) as Void {
        mHandler = handler;
        try {
            Notifications.registerForNotificationMessages(method(:_onMessage));
        } catch (e) {
            // The module is not available; the app keeps working without
            // on-watch actions.
        }
    }

    //! The callback of Toybox.Notifications.
    private static function _onMessage(message as Notifications.NotificationMessage) as Void {
        var handler = mHandler;
        if (handler == null || message == null) {
            return;
        }
        var notificationId = "";
        var actionId = "";
        var type = ACTION_DISMISSED;
        if (message.type == Notifications.NOTIFICATION_MESSAGE_TYPE_SELECTED) {
            type = ACTION_SELECTED;
            var parsed = _split(Values.string(message.action));
            notificationId = parsed[0] as Lang.String;
            actionId = parsed[1] as Lang.String;
        }
        if (notificationId == null || notificationId == "") {
            notificationId = Values.string(message.data);
        }
        if (notificationId == null) {
            notificationId = "";
        }
        handler.invoke(notificationId, actionId, type);
    }

    //! Split "<notification id>|<action id>" into its two parts.
    private static function _split(text as Lang.String?) as Lang.Array {
        var notificationId = "";
        var actionId = "";
        if (text != null && text != "") {
            var separator = text.find("|");
            if (separator == null) {
                notificationId = text;
            } else {
                notificationId = text.substring(0, separator);
                actionId = text.substring(separator + 1, text.length());
            }
        }
        return [notificationId, actionId];
    }

    //! Raise a system notification.
    //!
    //! @param title          The headline.
    //! @param body           The text below the headline.
    //! @param actions        Rows of [actionId, label], may be null.
    //! @param notificationId The id of the notification in the bridge queue.
    static function show(
        title as Lang.String,
        body as Lang.String,
        actions as Lang.Array?,
        notificationId as Lang.String
    ) as Void {
        var options = {
            :body => body == null ? "" : body,
            // The notification id travels back to the app when the user
            // picks the default action, which starts the app.
            :data => notificationId == null ? "" : notificationId,
            // Keep older notifications on screen; the app shows the whole
            // queue in its inbox anyway.
            :dismissPrevious => false
        };
        if (actions != null && actions.size() > 0) {
            var list = [];
            for (var i = 0; i < actions.size(); i++) {
                var action = actions[i] as Lang.Array;
                if (action == null || action.size() < 2) {
                    continue;
                }
                var actionId = Values.string(action[0]);
                if (actionId == null) {
                    actionId = "";
                }
                list.add({
                    :label => action[1] as Lang.String,
                    :data => (notificationId == null ? "" : notificationId) + "|" + actionId
                });
            }
            if (list.size() > 0) {
                options[:actions] = list;
            }
        }
        try {
            Notifications.showNotification(title, body == null ? "" : body, options);
        } catch (e) {
            // A device without the module throws here; the app keeps
            // working, the notification is simply not shown.
        }
    }

    //! The Venu build shows a notification instead of asking for a wake up.
    static function wake(message as Lang.String) as Void {
    }
}
