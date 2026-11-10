//
// The HTTP transport used to talk to the Garmin Home Assistant bridge.
//
// Everything goes through Toybox.Communications.makeWebRequest().  On a
// watch the request travels over Bluetooth LE through the paired phone and
// from there over the mobile network; the Edge 1040 and the Venu 4 also have
// Wi-Fi, so the same code reaches the bridge directly when a Wi-Fi profile
// is available.
//
// Two properties of the Connect IQ transport shape the implementation:
//
//   * There is no :body option before Connect IQ 6.0.3 and the Edge 1040
//     runs 6.0.0, so a request body cannot be relied upon.  Every POST
//     therefore carries its JSON document twice: once in the "json" query
//     parameter and once in the "json" form field.  Depending on the
//     runtime the parameters of a POST end up in the body or in the URL,
//     and the bridge accepts both shapes (see
//     bridge/src/garmin_bridge/app.py, _normalise_body).
//
//   * Responses are parsed by the runtime when :responseType is
//     HTTP_RESPONSE_CONTENT_TYPE_JSON, so the callback receives a
//     Toybox.Lang.Dictionary and no JSON parser is needed on the watch.
//
// Only one request is in flight at a time.  The client keeps the remaining
// requests in a queue and starts the next one when the previous callback
// arrives, so the single response handler always belongs to the request
// that is currently running.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Communications;
import Toybox.Lang;
import Toybox.Time;

(:background)
class HttpClient {

    //! Header carrying the id of the calling watch.
    static const HEADER_WATCH_ID as Lang.String = "X-Garmin-Watch-Id";
    //! Header carrying the bearer token.
    static const HEADER_AUTHORIZATION as Lang.String = "Authorization";
    //! Header describing the request body.
    static const HEADER_CONTENT_TYPE as Lang.String = "Content-Type";

    //! Query parameter the bridge looks at when it has to normalise a
    //! request body.
    static const PARAM_JSON as Lang.String = "json";

    //! How long a cached response stays usable, in seconds.
    static const CACHE_TTL as Lang.Number = 900;

    private var mBaseUrl as Lang.String = "";
    private var mToken as Lang.String = "";
    private var mWatchId as Lang.String = "";

    //! Last successful response per cache key.  The cache lets the watch
    //! keep showing the last known state while the bridge is unreachable.
    private var mCache as Lang.Dictionary = {};
    //! Timestamp of the cached responses, used to expire them.
    private var mCacheTime as Lang.Dictionary = {};

    //! Requests that have not been sent yet.  Each entry is a Dictionary
    //! with the keys "method", "path", "callback" and "cache".
    private var mQueue as Lang.Array = [];
    //! Index of the first entry of mQueue that has not been sent yet.
    //!
    //! Lang.Array has no shift(), so the queue is drained with an index
    //! instead of copying the array for every request.  The head is moved
    //! back to the front once the consumed part is at least half of the
    //! array, which keeps the memory use bounded without allocating on
    //! every request.
    private var mQueueHead as Lang.Number = 0;
    //! True while a request is waiting for its response.
    private var mInFlight as Lang.Boolean = false;
    //! The last error code that was seen.
    private var mLastError as Lang.Number = 0;

    //! The callback of the request that is currently in flight.
    private var mCurrentCallback as Lang.Method? = null;
    //! The cache key of the request that is currently in flight.
    private var mCurrentCacheKey as Lang.String? = null;

    function initialize(baseUrl as Lang.String, token as Lang.String, watchId as Lang.String) {
        mBaseUrl = baseUrl == null ? "" : baseUrl;
        mToken = token == null ? "" : token;
        mWatchId = watchId == null ? "" : watchId;
    }

    //! Replace the credentials, for example after the bridge issued a device
    //! specific token.
    function setCredentials(baseUrl as Lang.String, token as Lang.String) as Void {
        if (baseUrl != null) {
            mBaseUrl = baseUrl;
        }
        if (token != null) {
            mToken = token;
        }
    }

    function baseUrl() as Lang.String {
        return mBaseUrl;
    }

    function watchId() as Lang.String {
        return mWatchId;
    }

    function setWatchId(watchId as Lang.String) as Void {
        mWatchId = watchId == null ? "" : watchId;
    }

    //! True while at least one request is queued or in flight.
    function busy() as Lang.Boolean {
        return mInFlight || mQueue.size() > mQueueHead;
    }

    //! The last error code that was seen, 0 when nothing went wrong.
    function lastError() as Lang.Number {
        return mLastError;
    }

    //! Forget the cached responses, for example after the credentials
    //! changed.
    function clearCache() as Void {
        mCache = {};
        mCacheTime = {};
    }

    //! The cached response for a key, or null when there is none or when it
    //! has expired.
    function cached(key as Lang.String) as Lang.Dictionary? {
        if (key == null || !mCache.hasKey(key)) {
            return null;
        }
        var stamp = mCacheTime.get(key) as Lang.Number;
        if (stamp == null) {
            return null;
        }
        if (Time.now().value() - stamp > CACHE_TTL) {
            mCache.remove(key);
            mCacheTime.remove(key);
            return null;
        }
        return mCache.get(key) as Lang.Dictionary;
    }

    //! Perform a GET request.
    //!
    //! @param path      Path and query string, for example "/v1/entities".
    //! @param callback  Called with (responseCode, data).
    //! @param cacheKey  When set, a successful response is remembered under
    //!                  this key.
    function get(path as Lang.String, callback as Lang.Method, cacheKey as Lang.String?) as Void {
        _enqueue(Communications.HTTP_REQUEST_METHOD_GET, path, null, callback, cacheKey);
    }

    //! Perform a POST request whose body is a JSON object.
    //!
    //! The document travels in the "json" query parameter and in the "json"
    //! form field, because Connect IQ 6.0.0 -- the version on the Edge 1040
    //! -- has no :body option.  The bridge accepts both shapes.
    function post(path as Lang.String, payload as Lang.Dictionary, callback as Lang.Method) as Void {
        var document = Json.encode(payload);
        var url = path;
        if (url.find("?") == null) {
            url += "?";
        } else {
            url += "&";
        }
        url += PARAM_JSON + "=" + Json.urlEncode(document);
        _enqueue(Communications.HTTP_REQUEST_METHOD_POST, url, { PARAM_JSON => document }, callback, null);
    }

    private function _enqueue(
        method as Lang.Number,
        path as Lang.String,
        parameters as Lang.Dictionary?,
        callback as Lang.Method,
        cacheKey as Lang.String?
    ) as Void {
        mQueue.add({
            "method" => method,
            "path" => path,
            "parameters" => parameters,
            "callback" => callback,
            "cache" => cacheKey
        });
        if (!mInFlight) {
            _pump();
        }
    }

    //! Start the next queued request.
    private function _pump() as Void {
        if (mQueue.size() <= mQueueHead) {
            mInFlight = false;
            mQueue = [];
            mQueueHead = 0;
            return;
        }
        var entry = mQueue[mQueueHead] as Lang.Dictionary;
        mQueueHead++;
        // Drop the consumed part of the queue once it is worth it.
        if (mQueueHead >= 4 && mQueueHead * 2 >= mQueue.size()) {
            mQueue = mQueue.slice(mQueueHead);
            mQueueHead = 0;
        }
        var method = entry.get("method") as Lang.Number;
        var path = entry.get("path") as Lang.String;
        var cacheKey = entry.get("cache") as Lang.String;
        var callback = entry.get("callback") as Lang.Method;
        var parameters = entry.get("parameters") as Lang.Dictionary;

        if (mBaseUrl == "") {
            mInFlight = false;
            if (callback != null) {
                callback.invoke(-1, null);
            }
            _pump();
            return;
        }

        var headers = {
            HEADER_AUTHORIZATION => "Bearer " + mToken,
            HEADER_WATCH_ID => mWatchId
        };
        if (method == Communications.HTTP_REQUEST_METHOD_POST) {
            // The body travels in the form fields, so the request looks
            // like a form submission to the bridge.
            headers[HEADER_CONTENT_TYPE] = Communications.REQUEST_CONTENT_TYPE_URL_ENCODED;
        }
        var options = {
            :method => method,
            :headers => headers,
            :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON
        };

        mInFlight = true;
        mCurrentCallback = callback;
        mCurrentCacheKey = cacheKey;
        try {
            Communications.makeWebRequest(mBaseUrl + path, parameters, options, method(:_onResponse));
        } catch (e) {
            // An invalid URL or a missing permission throws instead of
            // calling back.  Report it like a network failure.
            mInFlight = false;
            mLastError = -1;
            if (callback != null) {
                callback.invoke(-1, null);
            }
            _pump();
        }
    }

    //! The single response handler of the client.
    private function _onResponse(code as Lang.Number, data as Lang.Dictionary or Lang.String or Null) as Void {
        mInFlight = false;
        var callback = mCurrentCallback;
        var cacheKey = mCurrentCacheKey;
        mCurrentCallback = null;
        mCurrentCacheKey = null;

        var document = Values.dictionary(data);
        if (code == 200) {
            mLastError = 0;
            if (document != null && cacheKey != null) {
                mCache.put(cacheKey, document);
                mCacheTime.put(cacheKey, Time.now().value());
            }
        } else {
            mLastError = code;
        }
        if (callback != null) {
            callback.invoke(code, document);
        }
        _pump();
    }

    //! A short description of an error code, suitable for the screen.
    static function describe(code as Lang.Number) as Lang.String {
        if (code == null) {
            return "unknown error";
        }
        if (code == 0) {
            return "ok";
        }
        if (code == 401 || code == 403) {
            return "not authorised";
        }
        if (code == 404) {
            return "not found";
        }
        if (code == Communications.NETWORK_REQUEST_TIMED_OUT) {
            return "timeout";
        }
        if (code == Communications.BLE_CONNECTION_UNAVAILABLE) {
            return "no phone link";
        }
        if (code == Communications.BLE_HOST_TIMEOUT || code == Communications.BLE_SERVER_TIMEOUT) {
            return "phone timeout";
        }
        if (code == Communications.NETWORK_RESPONSE_TOO_LARGE) {
            return "response too large";
        }
        if (code == Communications.NETWORK_RESPONSE_OUT_OF_MEMORY) {
            return "out of memory";
        }
        if (code == Communications.INVALID_HTTP_BODY_IN_NETWORK_RESPONSE) {
            return "bad response";
        }
        if (code == Communications.UNSUPPORTED_CONTENT_TYPE_IN_RESPONSE) {
            return "bad content type";
        }
        if (code == Communications.SECURE_CONNECTION_REQUIRED) {
            return "https required";
        }
        if (code == Communications.REQUEST_CANCELLED) {
            return "cancelled";
        }
        if (code == Communications.BLE_REQUEST_TOO_LARGE) {
            return "request too large";
        }
        if (code < 0) {
            return "network error";
        }
        return "error " + code.toString();
    }

    //! True when the request may succeed later without any user action.
    static function isTransient(code as Lang.Number) as Lang.Boolean {
        if (code == null || code >= 0) {
            return false;
        }
        return code != Communications.INVALID_HTTP_BODY_IN_REQUEST &&
               code != Communications.INVALID_HTTP_METHOD_IN_REQUEST &&
               code != Communications.INVALID_HTTP_HEADER_FIELDS_IN_REQUEST &&
               code != Communications.SECURE_CONNECTION_REQUIRED;
    }
}
