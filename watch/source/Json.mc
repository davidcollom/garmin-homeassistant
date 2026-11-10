//
// A very small JSON writer.
//
// Connect IQ has no Toybox.Json module, so a request body has to be built
// by hand.  The response side does not need a parser: asking
// Communications.makeWebRequest() for
// Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON makes the runtime decode
// the body and hand a Toybox.Lang.Dictionary to the callback.
//
// The writer therefore only has to handle the values this app sends:
// strings, numbers, booleans, arrays, dictionaries and null.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;

(:background)
class Json {

    //! Encode a value as a JSON document.
    static function encode(value as Object?) as Lang.String {
        if (value == null) {
            return "null";
        }
        if (value instanceof Lang.Boolean) {
            return (value as Lang.Boolean) ? "true" : "false";
        }
        if (value instanceof Lang.String) {
            return _quote(value as Lang.String);
        }
        if (value instanceof Lang.Number) {
            return (value as Lang.Number).toString();
        }
        if (value instanceof Lang.Double) {
            return _double(value as Lang.Double);
        }
        if (value instanceof Lang.Float) {
            return _double((value as Lang.Float).toDouble());
        }
        if (value instanceof Lang.Long) {
            return (value as Lang.Long).toString();
        }
        if (value instanceof Lang.Array) {
            return _array(value as Lang.Array);
        }
        if (value instanceof Lang.Dictionary) {
            return _dictionary(value as Lang.Dictionary);
        }
        return _quote(value.toString());
    }

    //! Percent encode a string so that it can be used as a query parameter
    //! value.  Only the unreserved characters of RFC 3986 survive, which
    //! keeps the encoding unambiguous for both the bridge and the watch.
    static function urlEncode(text as Lang.String) as Lang.String {
        if (text == null) {
            return "";
        }
        var bytes = text.toUtf8Array();
        var encoded = "";
        for (var i = 0; i < bytes.size(); i++) {
            var byte = bytes[i] as Lang.Number;
            if ((byte >= 48 && byte <= 57) ||
                (byte >= 65 && byte <= 90) ||
                (byte >= 97 && byte <= 122) ||
                byte == 45 || byte == 46 || byte == 95 || byte == 126) {
                encoded += byte.toChar().toString();
            } else {
                encoded += "%" + byte.format("%02X");
            }
        }
        return encoded;
    }

    //! Encode a dictionary as a query string, for example "a=1&b=2".
    static function encodeQuery(parameters as Lang.Dictionary?) as Lang.String {
        if (parameters == null) {
            return "";
        }
        var query = "";
        var keys = parameters.keys();
        for (var i = 0; i < keys.size(); i++) {
            var key = keys[i] as Lang.String;
            var value = parameters.get(key);
            if (value == null) {
                continue;
            }
            if (query != "") {
                query += "&";
            }
            query += urlEncode(key) + "=" + urlEncode(encode(value));
        }
        return query;
    }

    private static function _quote(text as Lang.String) as Lang.String {
        var quoted = "\"";
        var chars = text.toCharArray();
        for (var i = 0; i < chars.size(); i++) {
            var code = (chars[i] as Lang.Char).toNumber();
            if (code == 34) {
                quoted += "\\\"";
            } else if (code == 92) {
                quoted += "\\\\";
            } else if (code == 8) {
                quoted += "\\b";
            } else if (code == 9) {
                quoted += "\\t";
            } else if (code == 10) {
                quoted += "\\n";
            } else if (code == 12) {
                quoted += "\\f";
            } else if (code == 13) {
                quoted += "\\r";
            } else if (code < 32) {
                quoted += "\\u" + code.format("%04X");
            } else {
                // Everything else is emitted unchanged; the string is UTF-8
                // and the bridge decodes the body as UTF-8.
                quoted += (chars[i] as Lang.Char).toString();
            }
        }
        return quoted + "\"";
    }

    private static function _array(items as Lang.Array) as Lang.String {
        var encoded = "[";
        for (var i = 0; i < items.size(); i++) {
            if (i > 0) {
                encoded += ",";
            }
            encoded += encode(items[i]);
        }
        return encoded + "]";
    }

    private static function _dictionary(map as Lang.Dictionary) as Lang.String {
        var encoded = "{";
        var keys = map.keys();
        var first = true;
        for (var i = 0; i < keys.size(); i++) {
            var key = keys[i];
            if (!first) {
                encoded += ",";
            }
            first = false;
            encoded += _quote(key.toString()) + ":" + encode(map.get(key));
        }
        return encoded + "}";
    }

    //! Format a double without an exponent and without trailing zeros.
    private static function _double(value as Lang.Double) as Lang.String {
        var integral = value.toNumber();
        if (integral.toDouble() == value) {
            return integral.toString();
        }
        var text = value.format("%.4f");
        if (text == null) {
            return integral.toString();
        }
        return _trimZeros(text);
    }

    //! Remove trailing zeros and a trailing decimal point.
    private static function _trimZeros(text as Lang.String) as Lang.String {
        var end = text.length();
        while (end > 0) {
            var last = text.substring(end - 1, end);
            if (last == "0") {
                end--;
                continue;
            }
            if (last == ".") {
                end--;
            }
            break;
        }
        return text.substring(0, end);
    }
}
