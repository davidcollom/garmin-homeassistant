//
// The bridge API, expressed in the terms of the Garmin Home Assistant
// bridge (bridge/src/garmin_bridge/app.py).
//
// Every callback has the same shape: (responseCode as Number,
// data as Dictionary?).  A positive response code is the HTTP status, a
// negative one is a Connect IQ transport error; HttpClient.describe()
// turns both into something that fits on the screen.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;

(:background)
class BridgeClient {

    //! Base path of the watch facing API.
    static const PATH_ENTITIES as Lang.String = "/v1/entities";
    static const PATH_COMMANDS as Lang.String = "/v1/commands";
    static const PATH_NOTIFICATIONS as Lang.String = "/v1/notifications";
    static const PATH_EVENTS as Lang.String = "/v1/events";
    static const PATH_CONFIG as Lang.String = "/v1/config";
    static const PATH_REGISTER as Lang.String = "/v1/watches/register";

    private var mHttp as HttpClient;

    function initialize(baseUrl as Lang.String, token as Lang.String, watchId as Lang.String) {
        mHttp = new HttpClient(baseUrl, token, watchId);
    }

    //! The underlying transport, used for the cache and the error state.
    function http() as HttpClient {
        return mHttp;
    }

    function baseUrl() as Lang.String {
        return mHttp.baseUrl();
    }

    function setCredentials(baseUrl as Lang.String, token as Lang.String) as Void {
        mHttp.setCredentials(baseUrl, token);
        mHttp.clearCache();
    }

    function setWatchId(watchId as Lang.String) as Void {
        mHttp.setWatchId(watchId);
    }

    //! Register the watch and ask for a device specific token.
    function register(
        name as Lang.String,
        model as Lang.String,
        apiLevel as Lang.Number,
        capabilities as Lang.Dictionary,
        callback as Lang.Method
    ) as Void {
        var payload = {
            "watch_id" => mHttp.watchId(),
            "name" => name,
            "model" => model,
            "api_level" => apiLevel,
            "capabilities" => capabilities
        };
        mHttp.post(PATH_REGISTER, payload, callback);
    }

    //! Read the server side watch configuration.
    function fetchConfig(callback as Lang.Method) as Void {
        mHttp.get(PATH_CONFIG, callback, "config");
    }

    //! Read the entities that changed after a revision.
    //!
    //! @param since Revision the watch already knows about, 0 for a full
    //!             list.
    function fetchEntities(since as Lang.Number, callback as Lang.Method) as Void {
        mHttp.get(PATH_ENTITIES + "?since=" + since.toString(), callback, "entities");
    }

    //! Read one page of the entity list.
    function fetchEntitiesPage(offset as Lang.Number, limit as Lang.Number, callback as Lang.Method) as Void {
        mHttp.get(
            PATH_ENTITIES + "?limit=" + limit.toString() + "&offset=" + offset.toString(),
            callback,
            null
        );
    }

    //! Read the notifications that are still pending for this watch.
    function fetchNotifications(since as Lang.Number, callback as Lang.Method) as Void {
        mHttp.get(PATH_NOTIFICATIONS + "?since=" + since.toString(), callback, "notifications");
    }

    //! Acknowledge a notification and pass the chosen action on.
    function ackNotification(notificationId as Lang.String, action as Lang.String?, callback as Lang.Method) as Void {
        var payload = {};
        if (action != null && action != "") {
            payload["action"] = action;
        }
        mHttp.post(
            PATH_NOTIFICATIONS + "/" + Json.urlEncode(notificationId) + "/ack",
            payload,
            callback
        );
    }

    //! Run a command against Home Assistant.
    //!
    //! @param cmd      One of "toggle", "turn_on", "turn_off", "open",
    //!                 "close", "set_level", "set_value" or "service".
    //! @param entityId Target entity, may be null for "service".
    //! @param data     Additional service data, may be null.
    function sendCommand(
        cmd as Lang.String,
        entityId as Lang.String?,
        data as Lang.Dictionary?,
        callback as Lang.Method
    ) as Void {
        var payload = { "cmd" => cmd };
        if (entityId != null && entityId != "") {
            payload["entity_id"] = entityId;
        }
        if (data != null) {
            payload["data"] = data;
        }
        mHttp.post(PATH_COMMANDS, payload, callback);
    }

    //! Run an arbitrary Home Assistant service call.
    //!
    //! @param entityId Target entity, may be null.
    //! @param service  The service name, for example "alarm_arm_away".
    //! @param domain   The domain, derived from the entity when null.
    //! @param data     Additional service data, may be null.
    function sendService(
        entityId as Lang.String?,
        service as Lang.String,
        domain as Lang.String?,
        data as Lang.Dictionary?,
        callback as Lang.Method
    ) as Void {
        var payload = {
            "cmd" => "service",
            "service" => service
        };
        if (entityId != null && entityId != "") {
            payload["entity_id"] = entityId;
        }
        if (domain != null && domain != "") {
            payload["domain"] = domain;
        }
        if (data != null) {
            payload["data"] = data;
        }
        mHttp.post(PATH_COMMANDS, payload, callback);
    }

    //! Report telemetry or a button press.
    function sendEvent(
        type as Lang.String,
        battery as Lang.Number?,
        steps as Lang.Number?,
        heartRate as Lang.Number?,
        button as Lang.String?,
        message as Lang.String?,
        callback as Lang.Method
    ) as Void {
        var payload = { "type" => type };
        if (battery != null) {
            payload["battery"] = battery;
        }
        if (steps != null) {
            payload["steps"] = steps;
        }
        if (heartRate != null) {
            payload["heart_rate"] = heartRate;
        }
        if (button != null) {
            payload["button"] = button;
        }
        if (message != null) {
            payload["message"] = message;
        }
        mHttp.post(PATH_EVENTS, payload, callback);
    }
}
