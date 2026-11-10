//
// Type tolerant accessors for values that arrive over the wire.
//
// Connect IQ does not publish the concrete classes its JSON deserialiser
// produces.  The only guarantee is that a JSON object arrives as a
// Toybox.Lang.Dictionary.  Numbers are the awkward case: a JSON integer is
// normally a Toybox.Lang.Number while a JSON float may be a
// Toybox.Lang.Double, and Toybox.Lang.Double is *not* a
// Toybox.Lang.Number -- the compiler rejects
//
//     takesNumber(1.5d)        // ERROR: Invalid '$.Toybox.Lang.Double'
//
// so a direct "as Lang.Number" cast can silently yield null.
//
// Every value that comes off the wire therefore goes through these helpers
// instead of being cast directly.  They accept the union of all plausible
// runtime representations, which makes the watch tolerant of both the
// documented and the undocumented behaviour of the deserialiser.
//
// Two more rules of the Monkey C type system matter here:
//
//   * A local variable can never carry an explicit type, so the helpers
//     return nullable types and the callers decide what an absent value
//     means.
//   * Reading a member of a Lang.Array or a Lang.Dictionary yields an
//     untyped value, which cannot be passed to a typed parameter.  The
//     helpers below take a Lang.Object and the "item" helper performs the
//     cast that turns an untyped array element into an object.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;

(:background)
class Values {

    //! The value at an index of an array, or null when the index is out of
    //! range.
    //!
    //! Lang.Array hands out untyped values, so the element has to be cast
    //! before it can be passed to a typed parameter.
    static function item(source as Lang.Array?, index as Lang.Number) as Lang.Object? {
        if (source == null || index == null || index < 0 || index >= source.size()) {
            return null;
        }
        return source[index] as Lang.Object;
    }

    //! A numeric value as a plain 32 bit integer, or null when the value is
    //! not numeric at all.
    static function number(value as Lang.Object?) as Lang.Number? {
        if (value == null) {
            return null;
        }
        // The floating point classes are checked first: they are siblings of
        // Lang.Number, not subclasses of it.
        if (value instanceof Lang.Double) {
            return (value as Lang.Double).toNumber();
        }
        if (value instanceof Lang.Float) {
            return (value as Lang.Float).toNumber();
        }
        if (value instanceof Lang.Long) {
            return (value as Lang.Long).toNumber();
        }
        if (value instanceof Lang.Number) {
            return value as Lang.Number;
        }
        if (value instanceof Lang.String) {
            return (value as Lang.String).toNumber();
        }
        if (value instanceof Lang.Boolean) {
            return (value as Lang.Boolean) ? 1 : 0;
        }
        return null;
    }

    //! A numeric value as a double, so that fractional attributes such as a
    //! climate setpoint survive.
    static function double(value as Lang.Object?) as Lang.Double? {
        if (value == null) {
            return null;
        }
        if (value instanceof Lang.Double) {
            return value as Lang.Double;
        }
        if (value instanceof Lang.Float) {
            return (value as Lang.Float).toDouble();
        }
        if (value instanceof Lang.Long) {
            return (value as Lang.Long).toDouble();
        }
        if (value instanceof Lang.Number) {
            return (value as Lang.Number).toDouble();
        }
        if (value instanceof Lang.String) {
            return (value as Lang.String).toDouble();
        }
        return null;
    }

    //! A string value, or null.
    static function string(value as Lang.Object?) as Lang.String? {
        if (value == null) {
            return null;
        }
        if (value instanceof Lang.String) {
            return value as Lang.String;
        }
        if (value instanceof Lang.Double) {
            return (value as Lang.Double).toString();
        }
        if (value instanceof Lang.Float) {
            return (value as Lang.Float).toDouble().toString();
        }
        if (value instanceof Lang.Long) {
            return (value as Lang.Long).toString();
        }
        if (value instanceof Lang.Number) {
            return (value as Lang.Number).toString();
        }
        if (value instanceof Lang.Boolean) {
            return (value as Lang.Boolean) ? "true" : "false";
        }
        if (value instanceof Lang.Char) {
            return (value as Lang.Char).toString();
        }
        return null;
    }

    //! A boolean value, or null.
    static function boolean(value as Lang.Object?) as Lang.Boolean? {
        if (value == null) {
            return null;
        }
        if (value instanceof Lang.Boolean) {
            return value as Lang.Boolean;
        }
        if (value instanceof Lang.Number) {
            return (value as Lang.Number) != 0;
        }
        if (value instanceof Lang.String) {
            var text = (value as Lang.String).toLower();
            return text == "true" || text == "1" || text == "yes";
        }
        return null;
    }

    //! An array value, or null.
    static function array(value as Lang.Object?) as Lang.Array? {
        if (value == null) {
            return null;
        }
        if (value instanceof Lang.Array) {
            return value as Lang.Array;
        }
        return null;
    }

    //! A dictionary value, or null.
    //!
    //! The generic parameters matter: the Connect IQ transport hands the
    //! response to the callback as a Lang.Dictionary<Object, Object> and a
    //! raw Lang.Dictionary is not the same type.
    static function dictionary(value as Lang.Object?) as Lang.Dictionary<Lang.Object, Lang.Object>? {
        if (value == null) {
            return null;
        }
        if (value instanceof Lang.Dictionary) {
            return value as Lang.Dictionary<Lang.Object, Lang.Object>;
        }
        return null;
    }

    //! The value of a dictionary entry, or null.  A missing key and a key
    //! that is present but null are deliberately treated the same way.
    static function member(
        container as Lang.Dictionary<Lang.Object, Lang.Object>?,
        key as Lang.String
    ) as Lang.Object? {
        if (container == null || key == null) {
            return null;
        }
        if (!container.hasKey(key)) {
            return null;
        }
        return container.get(key) as Lang.Object;
    }

    //! The value of a dictionary entry as a number, or a fallback.
    static function memberNumber(
        container as Lang.Dictionary<Lang.Object, Lang.Object>?,
        key as Lang.String,
        fallback as Lang.Number
    ) as Lang.Number {
        var value = number(member(container, key));
        if (value == null) {
            return fallback;
        }
        return value;
    }

    //! The value of a dictionary entry as a string, or a fallback.
    static function memberString(
        container as Lang.Dictionary<Lang.Object, Lang.Object>?,
        key as Lang.String,
        fallback as Lang.String
    ) as Lang.String {
        var value = string(member(container, key));
        if (value == null) {
            return fallback;
        }
        return value;
    }

    //! The value of a dictionary entry as a boolean, or a fallback.
    static function memberBoolean(
        container as Lang.Dictionary<Lang.Object, Lang.Object>?,
        key as Lang.String,
        fallback as Lang.Boolean
    ) as Lang.Boolean {
        var value = boolean(member(container, key));
        if (value == null) {
            return fallback;
        }
        return value;
    }

    //! Render a numeric value for the screen.  Whole numbers are printed
    //! without a fractional part, everything else with at most one decimal.
    static function format(value as Lang.Object?) as Lang.String {
        var number = double(value);
        if (number == null) {
            return "";
        }
        var integral = number.toNumber();
        if (integral.toDouble() == number) {
            return integral.toString();
        }
        var text = number.format("%.1f");
        if (text == null) {
            return integral.toString();
        }
        return text;
    }
}
