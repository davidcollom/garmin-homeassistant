//
// Notification presenter for the devices that do not implement
// Toybox.Notifications: the Edge 1040 and the Edge 1040 Solar.
//
// The Edge 1040 is excluded from the supported device list of
// https://developer.garmin.com/connect-iq/api-docs/Toybox/Notifications.html
// even though it runs Connect IQ 6.0, which is well above the 5.1.0 that
// the module requires.  The module is therefore not referenced at all in
// this build; the compiler would happily accept it, but the device would
// raise at runtime.
//
// The Edge shows a toast instead.  A toast carries text only, so there is
// no way to offer action buttons on the watch.  The second best thing is
// Background.requestApplicationWake(), which puts a confirmation dialog on
// the screen and opens the app when the user agrees.  The inbox of the app
// offers the actions of a notification, so nothing is lost.
//
// The Venu 4 build uses variants/notifications/NotificationPresenter.mc.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Background;
import Toybox.Lang;
using Toybox.WatchUi as Ui;

(:background)
class NotificationPresenter {

    //! The user picked one of the actions of the notification.
    static const ACTION_SELECTED as Lang.Number = 1;
    //! The user dismissed the notification without picking an action.
    static const ACTION_DISMISSED as Lang.Number = 0;

    //! The handler that receives the notification messages.
    private static var mHandler as Lang.Method? = null;

    //! False: this build cannot raise system notifications with actions.
    static function supportsSystemNotifications() as Lang.Boolean {
        return false;
    }

    //! True: this build can ask the user to open the app.
    static function supportsWakeRequest() as Lang.Boolean {
        return true;
    }

    //! There is no notification channel on this device.
    static function register(handler as Lang.Method) as Void {
        mHandler = handler;
    }

    //! Show a toast.
    //!
    //! @param title         The headline.
    //! @param body          The text below the headline.
    //! @param actions       Rows of [actionId, label], may be null.  The
    //!                       Edge cannot render them, so they are ignored.
    //! @param notificationId The id of the notification in the bridge queue.
    static function show(
        title as Lang.String,
        body as Lang.String,
        actions as Lang.Array?,
        notificationId as Lang.String
    ) as Void {
        var text = title == null ? "" : title;
        if (body != null && body != "") {
            text = text + ": " + body;
        }
        try {
            Ui.showToast(text, null);
        } catch (e) {
            // A toast is best effort; the foreground app still shows the
            // notification in its inbox.
        }
    }

    //! Ask the user to open the app.
    //!
    //! The message is limited to 255 bytes by the runtime.
    static function wake(message as Lang.String) as Void {
        var text = message == null ? "" : message;
        if (text.length() > 200) {
            text = text.substring(0, 200);
        }
        try {
            Background.requestApplicationWake(text);
        } catch (e) {
            // Only a background service may ask for a wake up.
        }
    }
}
