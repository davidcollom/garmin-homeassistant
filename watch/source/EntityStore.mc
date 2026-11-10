//
// In memory mirror of the entities and notifications the bridge exposes.
//
// The wire format is deliberately compact because it travels over Bluetooth
// LE.  An entity is a flat array instead of an object:
//
//     [id, name, domain, state, flags, areaIndex, value]
//
// and a notification is:
//
//     [id, timestamp, title, body, priority, actions, entityId]
//
// The layout matches the serialisers in bridge/src/garmin_bridge/models.py
// (CompactEntity and NotificationList).
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;

(:background)
class EntityStore {

    // -- capability flags, mirrored from the bridge ------------------------
    static const FLAG_TOGGLE as Lang.Number = 1;
    static const FLAG_BRIGHTNESS as Lang.Number = 2;
    static const FLAG_LEVEL as Lang.Number = 4;
    static const FLAG_OPEN_CLOSE as Lang.Number = 8;
    static const FLAG_SETPOINT as Lang.Number = 16;
    static const FLAG_PINNED as Lang.Number = 32;
    static const FLAG_PERCENT as Lang.Number = 64;

    // -- entity row columns ------------------------------------------------
    static const COL_ID as Lang.Number = 0;
    static const COL_NAME as Lang.Number = 1;
    static const COL_DOMAIN as Lang.Number = 2;
    static const COL_STATE as Lang.Number = 3;
    static const COL_FLAGS as Lang.Number = 4;
    static const COL_AREA as Lang.Number = 5;
    static const COL_VALUE as Lang.Number = 6;

    // -- notification row columns ------------------------------------------
    static const NOTIF_ID as Lang.Number = 0;
    static const NOTIF_TS as Lang.Number = 1;
    static const NOTIF_TITLE as Lang.Number = 2;
    static const NOTIF_BODY as Lang.Number = 3;
    static const NOTIF_PRIORITY as Lang.Number = 4;
    static const NOTIF_ACTIONS as Lang.Number = 5;
    static const NOTIF_ENTITY as Lang.Number = 6;

    //! Sort key for entities that have no area; the bridge uses the same
    //! trick so that both sides agree on the order.
    static const NO_AREA_RANK as Lang.Number = 999999;

    private var mEntities as Lang.Array = [];
    private var mAreas as Lang.Array = [];
    private var mNotifications as Lang.Array = [];
    private var mRevision as Lang.Number = 0;
    private var mCursor as Lang.Number = 0;

    function initialize() {
    }

    // -- entities ----------------------------------------------------------

    function size() as Lang.Number {
        return mEntities.size();
    }

    function revision() as Lang.Number {
        return mRevision;
    }

    function areas() as Lang.Array {
        return mAreas;
    }

    //! Row at the given index or null.
    function row(index as Lang.Number) as Lang.Array? {
        if (index == null || index < 0 || index >= mEntities.size()) {
            return null;
        }
        return mEntities[index] as Lang.Array;
    }

    //! Index of an entity id, or -1.
    function indexOf(entityId as Lang.String) as Lang.Number {
        if (entityId == null) {
            return -1;
        }
        for (var i = 0; i < mEntities.size(); i++) {
            if (_field(mEntities[i] as Lang.Array, COL_ID) == entityId) {
                return i;
            }
        }
        return -1;
    }

    function entityIdAt(index as Lang.Number) as Lang.String {
        var value = _field(row(index), COL_ID);
        return value == null ? "" : value;
    }

    function nameAt(index as Lang.Number) as Lang.String {
        var value = _field(row(index), COL_NAME);
        return value == null ? "" : value;
    }

    function domainAt(index as Lang.Number) as Lang.String {
        var value = _field(row(index), COL_DOMAIN);
        return value == null ? "" : value;
    }

    function stateAt(index as Lang.Number) as Lang.String {
        var value = _field(row(index), COL_STATE);
        return value == null ? "" : value;
    }

    function flagsAt(index as Lang.Number) as Lang.Number {
        var value = Values.number(_field(row(index), COL_FLAGS));
        return value == null ? 0 : value;
    }

    //! The numeric attribute of an entity, for example a brightness level.
    function valueAt(index as Lang.Number) as Object? {
        return _field(row(index), COL_VALUE);
    }

    //! The index into the area table, or -1 when the entity has no area.
    function areaIndexAt(index as Lang.Number) as Lang.Number {
        var value = Values.number(_field(row(index), COL_AREA));
        return value == null ? -1 : value;
    }

    //! The name of the area an entity belongs to, or an empty string.
    function areaNameAt(index as Lang.Number) as Lang.String {
        var area = areaIndexAt(index);
        if (area < 0 || area >= mAreas.size()) {
            return "";
        }
        var name = Values.string(mAreas[area]);
        return name == null ? "" : name;
    }

    //! True when the entity has the given capability flag.
    function hasFlag(index as Lang.Number, flag as Lang.Number) as Lang.Boolean {
        return (flagsAt(index) & flag) != 0;
    }

    //! Drop every entity, used before a full reload.
    function reset() as Void {
        mEntities = [];
        mRevision = 0;
    }

    //! Apply a snapshot received from the bridge.
    //!
    //! @param data       Parsed JSON response.
    //! @param replaceAll True when the response contains the complete list.
    //!
    //! @return True when the snapshot was understood.
    function applySnapshot(data as Lang.Dictionary, replaceAll as Lang.Boolean) as Lang.Boolean {
        if (data == null) {
            return false;
        }
        if (replaceAll) {
            mEntities = [];
        }
        var areas = Values.array(Values.member(data, "areas"));
        if (areas != null) {
            mAreas = areas;
        }
        var removed = Values.array(Values.member(data, "r"));
        if (removed != null) {
            for (var i = 0; i < removed.size(); i++) {
                var gone = Values.string(removed[i]);
                if (gone != null) {
                    _removeEntity(gone);
                }
            }
        }
        var rows = Values.array(Values.member(data, "e"));
        if (rows != null) {
            for (var i = 0; i < rows.size(); i++) {
                _upsert(rows[i] as Lang.Array);
            }
        }
        var revision = Values.number(Values.member(data, "rev"));
        if (revision != null) {
            mRevision = revision;
        }
        _sort();
        return true;
    }

    private function _removeEntity(entityId as Lang.String) as Void {
        for (var i = mEntities.size() - 1; i >= 0; i--) {
            if (_field(mEntities[i] as Lang.Array, COL_ID) == entityId) {
                mEntities.remove(i);
            }
        }
    }

    private function _upsert(row as Lang.Array) as Void {
        if (row == null || row.size() < 4) {
            return;
        }
        var entityId = Values.string(row[COL_ID]);
        if (entityId == null || entityId == "") {
            return;
        }
        for (var i = 0; i < mEntities.size(); i++) {
            if (_field(mEntities[i] as Lang.Array, COL_ID) == entityId) {
                mEntities[i] = row;
                return;
            }
        }
        mEntities.add(row);
    }

    //! Keep the list ordered the way the bridge ordered it: by area and
    //! then by name.  Entities without an area go last.
    private function _sort() as Void {
        var count = mEntities.size();
        for (var i = 1; i < count; i++) {
            var current = mEntities[i] as Lang.Array;
            var j = i - 1;
            while (j >= 0 && _compare(current, mEntities[j] as Lang.Array) < 0) {
                mEntities[j + 1] = mEntities[j];
                j--;
            }
            mEntities[j + 1] = current;
        }
    }

    private function _compare(a as Lang.Array, b as Lang.Array) as Lang.Number {
        var areaA = _areaRank(a);
        var areaB = _areaRank(b);
        if (areaA != areaB) {
            return areaA < areaB ? -1 : 1;
        }
        var nameA = Values.string(_field(a, COL_NAME));
        var nameB = Values.string(_field(b, COL_NAME));
        if (nameA == null) {
            nameA = "";
        }
        if (nameB == null) {
            nameB = "";
        }
        return nameA.toLower().compareTo(nameB.toLower());
    }

    private function _areaRank(row as Lang.Array) as Lang.Number {
        var area = Values.number(_field(row, COL_AREA));
        if (area == null || area < 0) {
            return NO_AREA_RANK;
        }
        return area;
    }

    //! Read a column of a row without caring whether the value arrived as a
    //! number, a double or a string.
    private function _field(row as Lang.Array?, column as Lang.Number) as Object? {
        if (row == null || column >= row.size()) {
            return null;
        }
        return row[column];
    }

    // -- notifications -----------------------------------------------------

    function notificationCount() as Lang.Number {
        return mNotifications.size();
    }

    function notificationAt(index as Lang.Number) as Lang.Array? {
        if (index == null || index < 0 || index >= mNotifications.size()) {
            return null;
        }
        return mNotifications[index] as Lang.Array;
    }

    function cursor() as Lang.Number {
        return mCursor;
    }

    //! Merge notifications received from the bridge.
    //!
    //! @return The number of notifications that were added.
    function applyNotifications(data as Lang.Dictionary) as Lang.Number {
        if (data == null) {
            return 0;
        }
        var added = 0;
        var rows = Values.array(Values.member(data, "n"));
        if (rows != null) {
            for (var i = 0; i < rows.size(); i++) {
                var row = rows[i] as Lang.Array;
                if (row == null) {
                    continue;
                }
                if (_hasNotification(Values.string(row[NOTIF_ID]))) {
                    continue;
                }
                mNotifications.add(row);
                added++;
            }
        }
        var cursor = Values.number(Values.member(data, "cursor"));
        if (cursor != null) {
            mCursor = cursor;
        }
        return added;
    }

    private function _hasNotification(notificationId as Lang.String?) as Lang.Boolean {
        if (notificationId == null) {
            return false;
        }
        for (var i = 0; i < mNotifications.size(); i++) {
            if (Values.string((mNotifications[i] as Lang.Array)[NOTIF_ID]) == notificationId) {
                return true;
            }
        }
        return false;
    }

    //! Forget a notification, for example after it was acknowledged.
    function removeNotification(notificationId as Lang.String) as Void {
        for (var i = mNotifications.size() - 1; i >= 0; i--) {
            var row = mNotifications[i] as Lang.Array;
            if (Values.string(row[NOTIF_ID]) == notificationId) {
                mNotifications.remove(i);
            }
        }
    }
}
