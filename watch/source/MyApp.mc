//
// Garmin Home Assistant - Connect IQ application entry point.
//
// The application object owns the view and its input delegate and nothing
// else; everything else is created lazily in getInitialView() so that the
// object stays cheap and the Connect IQ runtime only pays for what is on
// screen.
//
// The class carries the (:background) annotation because it provides a
// service delegate.  Every method that only makes sense in the foreground
// is annotated with (:typecheck(disableBackgroundCheck)), the way the
// Notifications sample of the SDK does it.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
using Toybox.Application as App;
import Toybox.Background;
import Toybox.Lang;
import Toybox.System;
import Toybox.Time;
using Toybox.WatchUi as Ui;

(:background)
class MyApp extends App.AppBase {

    //! The view.
    (:initialized)
    private var mView as MainView;
    //! The input delegate of the view.
    (:initialized)
    private var mDelegate as MainDelegate;
    //! The bridge client.
    (:initialized)
    private var mClient as BridgeClient;
    //! The in memory mirror of the bridge state.
    (:initialized)
    private var mStore as EntityStore;
    //! What the device can do.
    (:initialized)
    private var mCapabilities as Capabilities;
    //! The notification the app was launched from, if any.
    private var mLaunchedAction as Lang.Dictionary? = null;

    function initialize() {
        App.AppBase.initialize();
    }

    //! Called when the application is launched.
    //!
    //! Two things happen here: the background poll is scheduled and the
    //! launch reason is inspected.  When the user picks an action of a
    //! notification the system starts the app and hands the action over in
    //! the :launchedFromNotification entry of the state dictionary.
    function onStart(state as Lang.Dictionary?) as Void {
        _scheduleBackground();
        if (state != null) {
            var launched = state.get(:launchedFromNotification);
            if (launched != null) {
                mLaunchedAction = _parseAction(launched);
            }
        }
    }

    //! Called when the application is closed.
    function onStop(state as Lang.Dictionary?) as Void {
    }

    //! The background service that polls the notification queue.
    function getServiceDelegate() as [System.ServiceDelegate] {
        return [new BackgroundDelegate()];
    }

    //! The background service left a result behind.
    //!
    //! The payload only carries the number of notifications that were
    //! raised, the foreground app reads the queue itself.
    function onBackgroundData(data as App.PersistableType) as Void {
    }

    //! The first screen of the application.
    (:typecheck(disableBackgroundCheck))
    function getInitialView() as [Ui.Views] or [Ui.Views, Ui.InputDelegates] {
        if (mView == null) {
            mCapabilities = new Capabilities();
            mClient = new BridgeClient(Settings.bridgeUrl(), Settings.token(), Settings.watchId());
            mStore = new EntityStore();
            mView = new MainView(mClient, mStore);
            mDelegate = new MainDelegate(mView);
        }
        // The notification handler only exists in the foreground.
        NotificationPresenter.register(method(:onNotification));
        _handleLaunchedAction();
        return [mView, mDelegate];
    }

    //! The user picked an action of a notification or dismissed it.
    (:typecheck(disableBackgroundCheck))
    private function onNotification(notificationId as Lang.String, actionId as Lang.String, type as Lang.Number) as Void {
        if (notificationId == null || notificationId == "") {
            return;
        }
        var action = null;
        if (type == NotificationPresenter.ACTION_SELECTED && actionId != null && actionId != "") {
            action = actionId;
        }
        _acknowledge(notificationId, action);
    }

    //! The bridge answered an acknowledgement.
    (:typecheck(disableBackgroundCheck))
    private function onAcknowledge(code as Lang.Number, data as Lang.Dictionary?) as Void {
    }

    //! Tell the bridge that a notification was seen.
    private function _acknowledge(notificationId as Lang.String, action as Lang.String?) as Void {
        if (mClient == null || notificationId == null || notificationId == "") {
            return;
        }
        mClient.ackNotification(notificationId, action, method(:onAcknowledge));
    }

    //! Act on the notification the app was launched from.
    private function _handleLaunchedAction() as Void {
        if (mLaunchedAction == null) {
            return;
        }
        var launched = mLaunchedAction;
        mLaunchedAction = null;
        var notificationId = launched.get("n") as Lang.String;
        var action = launched.get("a") as Lang.String;
        if (action == null || action == "") {
            action = null;
        }
        _acknowledge(notificationId, action);
    }

    //! Read the action the app was launched with.
    //!
    //! The action data is the string "<notification id>|<action id>", but a
    //! dictionary with the keys "n" and "a" is accepted as well, because the
    //! exact shape the runtime hands over is not documented.
    private function _parseAction(data as Object?) as Lang.Dictionary? {
        if (data == null) {
            return null;
        }
        var notificationId = "";
        var actionId = "";
        var text = Values.string(data);
        if (text != null) {
            var separator = text.find("|");
            if (separator == null) {
                notificationId = text;
            } else {
                notificationId = text.substring(0, separator);
                actionId = text.substring(separator + 1, text.length());
            }
        } else {
            var map = Values.dictionary(data);
            if (map == null) {
                return null;
            }
            notificationId = Values.memberString(map, "n", "");
            actionId = Values.memberString(map, "a", "");
        }
        if (notificationId == "") {
            return null;
        }
        return { "n" => notificationId, "a" => actionId };
    }

    //! Ask the system to wake the app every few minutes.
    //!
    //! The Connect IQ runtime refuses a temporal event that is scheduled
    //! less than five minutes out, so the interval is clamped.
    private function _scheduleBackground() as Void {
        var interval = Settings.backgroundInterval();
        try {
            Background.registerForTemporalEvent(new Time.Duration(interval));
        } catch (e) {
            try {
                Background.registerForTemporalEvent(new Time.Duration(Settings.MIN_BACKGROUND_INTERVAL));
            } catch (e2) {
                // The device refused the event, the app still works.
            }
        }
    }
}
