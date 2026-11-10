//
// The Garmin Home Assistant watch user interface.
//
// The user interface is one WatchUi.View with three screens:
//
//   * the entity list, grouped by Home Assistant area,
//   * the inbox, listing the notifications the bridge still holds, and
//   * the detail screen of one entity or one notification.
//
// Connect IQ has no scroll view, so the list is paged by hand: the view
// keeps a window of rows (mTop) and moves that window one page at a time
// when the user swipes.  The rows themselves are WatchUi.Text objects that
// are re-used, so the memory cost does not grow with the number of
// entities.
//
// The geometry is derived from the device, never hard coded: the round
// Venu 4 and the rectangular Edge 1040 have very different shapes and the
// same source has to look right on both.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
using Toybox.Application as App;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;
import Toybox.System;
import Toybox.Time;
using Toybox.WatchUi as Ui;

class MainView extends Ui.View {

    // -- screens -----------------------------------------------------------
    static const SCREEN_LIST as Lang.Number = 0;
    static const SCREEN_INBOX as Lang.Number = 1;
    static const SCREEN_DETAIL as Lang.Number = 2;

    // -- what the detail screen shows -------------------------------------
    static const DETAIL_ENTITY as Lang.Number = 0;
    static const DETAIL_NOTIFICATION as Lang.Number = 1;

    // -- row kinds ---------------------------------------------------------
    static const ROW_AREA as Lang.Number = 0;
    static const ROW_ENTITY as Lang.Number = 1;
    static const ROW_NOTIFICATION as Lang.Number = 2;

    // -- geometry ----------------------------------------------------------
    //! Height of the title bar.
    static const HEADER_HEIGHT as Lang.Number = 22;
    //! Height of the status bar.
    static const FOOTER_HEIGHT as Lang.Number = 16;
    //! Height of one list row.
    static const ROW_HEIGHT as Lang.Number = 24;
    //! Height of one line of the detail screen.
    static const DETAIL_LINE_HEIGHT as Lang.Number = 20;
    //! Height of an action button.
    static const BUTTON_HEIGHT as Lang.Number = 30;
    //! Gap between two action buttons.
    static const BUTTON_GAP as Lang.Number = 6;
    //! Horizontal margin on a rectangular screen.
    static const MARGIN as Lang.Number = 8;
    //! Never allocate more row slots than this.
    static const MAX_ROWS as Lang.Number = 16;
    //! Number of action buttons the detail screen can show.
    static const MAX_ACTIONS as Lang.Number = 4;
    //! Width reserved for the state column of a row.
    static const VALUE_WIDTH as Lang.Number = 96;

    // -- colours -----------------------------------------------------------
    static const COLOR_TEXT as Lang.Number = Graphics.COLOR_WHITE;
    static const COLOR_DIM as Lang.Number = Graphics.COLOR_LT_GRAY;
    static const COLOR_AREA as Lang.Number = Graphics.COLOR_BLUE;
    static const COLOR_WARN as Lang.Number = Graphics.COLOR_ORANGE;
    static const COLOR_BUTTON as Lang.Number = Graphics.COLOR_DK_GRAY;
    static const COLOR_BUTTON_HI as Lang.Number = Graphics.COLOR_LT_GRAY;

    //! The bridge client.
    private var mClient as BridgeClient;
    //! The in memory mirror of the bridge state.
    private var mStore as EntityStore;
    //! What the device can do.
    private var mCapabilities as Capabilities;

    //! The screen that is shown.
    private var mScreen as Lang.Number = SCREEN_LIST;
    //! The rows of the current screen.
    private var mRows as Lang.Array = [];
    //! Index of the first visible row.
    private var mTop as Lang.Number = 0;
    //! Index of the selected entity or notification.
    private var mSelection as Lang.Number = 0;
    //! Index of the selected action on the detail screen.
    private var mActionIndex as Lang.Number = 0;
    //! What the detail screen describes.
    private var mDetailKind as Lang.Number = DETAIL_ENTITY;
    //! The actions of the detail screen.
    private var mActions as Lang.Array = [];

    //! Short status line, for example "12 entities".
    private var mStatus as Lang.String = "";
    //! Error line, empty when everything is fine.
    private var mError as Lang.String = "";
    //! True while a request is running.
    private var mBusy as Lang.Boolean = false;
    //! Seconds between two polls.
    private var mPollInterval as Lang.Number = 30;
    //! Unix time of the last poll.
    private var mLastPoll as Lang.Number = 0;
    //! True once the first poll has finished.
    private var mLoaded as Lang.Boolean = false;
    //! True once the watch registered itself with the bridge.
    private var mRegistered as Lang.Boolean = false;

    // -- drawables ---------------------------------------------------------
    private var mHeader as Ui.Text? = null;
    private var mFooter as Ui.Text? = null;
    private var mTitle as Ui.Text? = null;
    private var mSubtitle as Ui.Text? = null;
    private var mState as Ui.Text? = null;
    private var mValue as Ui.Text? = null;
    private var mBody as Ui.TextArea? = null;
    private var mRowNames as Lang.Array = [];
    private var mButtons as Lang.Array = [];
    private var mButtonLabels as Lang.Array = [];

    // -- geometry ----------------------------------------------------------
    private var mWidth as Lang.Number = 0;
    private var mHeight as Lang.Number = 0;
    private var mRound as Lang.Boolean = false;
    private var mCentre as Lang.Number = 0;
    private var mBodyTop as Lang.Number = 0;
    private var mBodyBottom as Lang.Number = 0;
    private var mRowsPerPage as Lang.Number = 1;
    private var mSlotCount as Lang.Number = 0;
    //! Moment of the last action, used to ignore a duplicated tap.
    private var mLastAction as Time.Moment? = null;
    //! Unix time of the last action, used to ignore a duplicated tap.
    private var mLastActionAt as Lang.Number = -1;
    //! The screen the detail screen was opened from.
    private var mReturnScreen as Lang.Number = SCREEN_LIST;

    function initialize(client as BridgeClient, store as EntityStore) {
        Ui.View.initialize();
        mClient = client;
        mStore = store;
        mCapabilities = new Capabilities();
        mPollInterval = Settings.pollInterval();
    }

    //! The store, so that the application can reach it.
    function store() as EntityStore {
        return mStore;
    }

    //! Build the layout.
    //!
    //! The static chrome comes from resources/layouts.xml, everything that
    //! depends on the content is created here.
    function onLayout(dc as Dc) as Void {
        mWidth = dc.getWidth();
        mHeight = dc.getHeight();
        mRound = mCapabilities.isRound();
        mCentre = mWidth / 2.0;

        var layout = Rez.Layouts.main(dc);
        mHeader = layout[0] as Ui.Text;
        mFooter = layout[1] as Ui.Text;

        mBodyTop = HEADER_HEIGHT + 2;
        mBodyBottom = mHeight - FOOTER_HEIGHT - 2;
        var bodyHeight = mBodyBottom - mBodyTop;
        if (bodyHeight < ROW_HEIGHT) {
            bodyHeight = ROW_HEIGHT;
        }
        mRowsPerPage = bodyHeight / ROW_HEIGHT;
        if (mRowsPerPage < 1) {
            mRowsPerPage = 1;
        }
        mSlotCount = mRowsPerPage;
        if (mSlotCount > MAX_ROWS) {
            mSlotCount = MAX_ROWS;
        }

        for (var i = 0; i < mSlotCount; i++) {
            var name = new Ui.Text({
                :text => "",
                :font => Graphics.FONT_SMALL,
                :color => COLOR_TEXT,
                :justification => Graphics.TEXT_JUSTIFY_LEFT,
                :locX => 0,
                :locY => 0,
                :width => mWidth,
                :height => ROW_HEIGHT,
                :identifier => "row" + i
            });
            mRowNames.add(name);
            layout.add(name);
        }

        mTitle = new Ui.Text({
            :text => "",
            :font => Graphics.FONT_MEDIUM,
            :color => COLOR_TEXT,
            :justification => Graphics.TEXT_JUSTIFY_LEFT,
            :locX => 0,
            :locY => 0,
            :width => mWidth,
            :height => DETAIL_LINE_HEIGHT,
            :identifier => "title"
        });
        layout.add(mTitle);

        mSubtitle = new Ui.Text({
            :text => "",
            :font => Graphics.FONT_XTINY,
            :color => COLOR_DIM,
            :justification => Graphics.TEXT_JUSTIFY_LEFT,
            :locX => 0,
            :locY => 0,
            :width => mWidth,
            :height => DETAIL_LINE_HEIGHT,
            :identifier => "subtitle"
        });
        layout.add(mSubtitle);

        mState = new Ui.Text({
            :text => "",
            :font => Graphics.FONT_LARGE,
            :color => COLOR_TEXT,
            :justification => Graphics.TEXT_JUSTIFY_LEFT,
            :locX => 0,
            :locY => 0,
            :width => mWidth,
            :height => DETAIL_LINE_HEIGHT + 8,
            :identifier => "state"
        });
        layout.add(mState);

        mValue = new Ui.Text({
            :text => "",
            :font => Graphics.FONT_SMALL,
            :color => COLOR_DIM,
            :justification => Graphics.TEXT_JUSTIFY_LEFT,
            :locX => 0,
            :locY => 0,
            :width => mWidth,
            :height => DETAIL_LINE_HEIGHT,
            :identifier => "value"
        });
        layout.add(mValue);

        mBody = new Ui.TextArea({
            :text => "",
            :font => [Graphics.FONT_SMALL, Graphics.FONT_XTINY],
            :color => COLOR_TEXT,
            :justification => Graphics.TEXT_JUSTIFY_LEFT,
            :locX => 0,
            :locY => 0,
            :width => mWidth,
            :height => DETAIL_LINE_HEIGHT * 2,
            :identifier => "body"
        });
        layout.add(mBody);

        for (var j = 0; j < MAX_ACTIONS; j++) {
            var button = new Ui.Button({
                :behavior => null,
                :background => COLOR_BUTTON,
                :stateDefault => COLOR_BUTTON,
                :stateHighlighted => COLOR_BUTTON_HI,
                :stateSelected => Graphics.COLOR_BLUE,
                :locX => 0,
                :locY => 0,
                :width => 1,
                :height => 1,
                :identifier => j
            });
            mButtons.add(button);
            layout.add(button);

            var label = new Ui.Text({
                :text => "",
                :font => Graphics.FONT_XTINY,
                :color => COLOR_TEXT,
                :justification => Graphics.TEXT_JUSTIFY_LEFT,
                :locX => 0,
                :locY => 0,
                :width => mWidth,
                :height => BUTTON_HEIGHT,
                :identifier => "action" + j
            });
            mButtonLabels.add(label);
            layout.add(label);
        }

        setLayout(layout);
    }

    //! The widest horizontal extent that is still on a round screen.
    //!
    //! On a round display a row that sits near the top or the bottom has
    //! much less room than one in the middle, so the extent is computed per
    //! row from the circle equation.
    //!
    //! @param top The top edge of the row.
    //! @return The left and the right edge of the row.
    private function _rowBounds(top as Lang.Number) as Lang.Array {
        if (!mRound) {
            return [MARGIN, mWidth - MARGIN];
        }
        var radius = mCentre;
        var dyTop = Math.abs(top - radius);
        var dyBottom = Math.abs(top + ROW_HEIGHT - radius);
        var sTop = radius * radius - dyTop * dyTop;
        var sBottom = radius * radius - dyBottom * dyBottom;
        if (sTop < sBottom) {
            sTop = sBottom;
        }
        if (sTop <= 0) {
            return [MARGIN, mWidth - MARGIN];
        }
        var half = Math.sqrt(sTop);
        var limit = radius - 4;
        if (half > limit) {
            half = limit;
        }
        return [radius - half, radius + half];
    }

    //! The vertical band that fits inside the round screen.
    //!
    //! @return The top and the bottom of the largest inscribed box.
    private function _safeBand() as Lang.Array {
        if (!mRound) {
            return [MARGIN, mHeight - MARGIN];
        }
        var radius = mCentre;
        var half = radius / 1.4143;
        return [radius - half, radius + half];
    }

    // -- data --------------------------------------------------------------

    //! Called when the screen becomes visible.
    function onShow() as Void {
        mLastPoll = 0;
        _refresh();
    }

    //! Called when the screen is hidden.
    function onHide() as Void {
    }

    //! Redraw the screen and poll when it is time.
    function onUpdate(dc as Dc) as Void {
        _render(dc);
        View.onUpdate(dc);
        _maybePoll();
    }

    //! Start a poll when the interval has passed.
    private function _maybePoll() as Void {
        if (mBusy || mLastPoll == 0) {
            return;
        }
        if (Time.now().value() - mLastPoll >= mPollInterval) {
            _refresh();
        }
    }

    //! Ask the bridge for the current state.
    private function _refresh() as Void {
        if (Settings.bridgeUrl() == "") {
            mError = App.loadResource(Rez.Strings.NotConfigured) as String;
            mStatus = "";
            mLoaded = true;
            _rebuildRows();
            return;
        }
        mBusy = true;
        mLastPoll = Time.now().value();
        if (Settings.deviceToken() == "" && !mRegistered) {
            // The first contact: the bridge hands out a token that is bound
            // to this watch.
            mRegistered = true;
            mClient.register(
                "Garmin " + mCapabilities.model(),
                mCapabilities.model(),
                mCapabilities.apiLevel(),
                mCapabilities.asDictionary(),
                method(:onRegistered)
            );
            return;
        }
        mClient.fetchConfig(method(:onConfig));
    }

    //! The bridge answered the registration.
    private function onRegistered(code as Lang.Number, data as Lang.Dictionary?) as Void {
        if (code == 200 && data != null) {
            var token = Values.memberString(data, "token", "");
            if (token != "") {
                Settings.setDeviceToken(token);
                mClient.setCredentials(Settings.bridgeUrl(), token);
            }
        } else {
            mError = HttpClient.describe(code);
            mBusy = false;
            return;
        }
        mClient.fetchConfig(method(:onConfig));
    }

    //! The server side configuration arrived.
    private function onConfig(code as Lang.Number, data as Lang.Dictionary?) as Void {
        if (code == 200 && data != null) {
            var interval = Values.memberNumber(data, "poll_interval", mPollInterval);
            if (interval < Settings.MIN_POLL_INTERVAL) {
                interval = Settings.MIN_POLL_INTERVAL;
            }
            mPollInterval = interval;
            Settings.setPageSize(Values.memberNumber(data, "page_size", 25));
            Settings.setServerMessage(Values.memberString(data, "message", ""));
        }
        mClient.fetchEntities(Settings.revision(), method(:onEntities));
    }

    //! The entity snapshot arrived.
    private function onEntities(code as Lang.Number, data as Lang.Dictionary?) as Void {
        if (code == 200 && data != null) {
            mStore.applySnapshot(data, Settings.revision() == 0);
            Settings.setRevision(mStore.revision());
            mError = "";
        } else {
            mError = HttpClient.describe(code);
        }
        mClient.fetchNotifications(Settings.notificationCursor(), method(:onNotifications));
    }

    //! The notification queue arrived.
    private function onNotifications(code as Lang.Number, data as Lang.Dictionary?) as Void {
        if (code == 200 && data != null) {
            mStore.applyNotifications(data);
            Settings.setNotificationCursor(mStore.cursor());
        } else if (code != 200) {
            mError = HttpClient.describe(code);
        }
        mBusy = false;
        mLoaded = true;
        _rebuildRows();
    }

    //! Build the rows of the current screen.
    private function _rebuildRows() as Void {
        mRows = [];
        if (mScreen == SCREEN_INBOX) {
            for (var i = 0; i < mStore.notificationCount(); i++) {
                mRows.add([ROW_NOTIFICATION, i]);
            }
            return;
        }
        var showAreas = Settings.showAreas();
        var previousArea = "";
        var haveArea = false;
        for (var i = 0; i < mStore.size(); i++) {
            if (showAreas) {
                var area = mStore.areaNameAt(i);
                if (!haveArea || area != previousArea) {
                    var heading = area;
                    if (heading == null || heading == "") {
                        heading = App.loadResource(Rez.Strings.UnknownArea) as String;
                    }
                    mRows.add([ROW_AREA, heading]);
                    previousArea = area;
                    haveArea = true;
                }
            }
            mRows.add([ROW_ENTITY, i]);
        }
        if (mSelection >= mStore.size()) {
            mSelection = mStore.size() - 1;
        }
        if (mSelection < 0) {
            mSelection = 0;
        }
    }

    //! The text of a row.
    private function _rowLabel(kind as Lang.Number, row as Lang.Array) as Lang.String {
        if (kind == ROW_AREA) {
            return row[1] as Lang.String;
        }
        if (kind == ROW_ENTITY) {
            var name = mStore.nameAt(row[1] as Lang.Number);
            if (name == null || name == "") {
                name = App.loadResource(Rez.Strings.UnnamedEntity) as String;
            }
            return name;
        }
        var notification = mStore.notificationAt(row[1] as Lang.Number);
        if (notification == null) {
            return "";
        }
        var title = Values.string(notification[EntityStore.NOTIF_TITLE]);
        return title == null ? "" : title;
    }

    //! The secondary text of a row.
    private function _rowValue(kind as Lang.Number, row as Lang.Array) as Lang.String {
        if (kind == ROW_ENTITY) {
            var index = row[1] as Lang.Number;
            var state = mStore.stateAt(index);
            var value = mStore.valueAt(index);
            if (value != null) {
                var number = Values.format(value);
                if (number != "" && number != state) {
                    state = state + "  " + number;
                }
            }
            return state;
        }
        if (kind == ROW_NOTIFICATION) {
            var notification = mStore.notificationAt(row[1] as Lang.Number);
            if (notification == null) {
                return "";
            }
            var body = Values.string(notification[EntityStore.NOTIF_BODY]);
            return body == null ? "" : body;
        }
        return "";
    }

    // -- rendering ---------------------------------------------------------

    //! Draw the screen.
    private function _render(dc as Dc) as Void {
        if (mScreen == SCREEN_DETAIL) {
            _renderDetail(dc);
        } else {
            _renderList(dc);
        }
    }

    //! Draw the list or the inbox.
    private function _renderList(dc as Dc) as Void {
        var title = App.loadResource(Rez.Strings.Entities) as String;
        if (mScreen == SCREEN_INBOX) {
            title = App.loadResource(Rez.Strings.Inbox) as String;
        }
        _setHeader(dc, title);
        _setFooter(dc, _footerText());

        for (var i = 0; i < mSlotCount; i++) {
            var text = mRowNames[i] as Ui.Text;
            var rowIndex = mTop + i;
            if (rowIndex >= mRows.size()) {
                text.setVisible(false);
                continue;
            }
            text.setVisible(true);
            var row = mRows[rowIndex] as Lang.Array;
            var kind = row[0] as Lang.Number;
            var top = mBodyTop + i * ROW_HEIGHT;
            var bounds = _rowBounds(top);
            var left = bounds[0] as Lang.Number;
            var right = bounds[1] as Lang.Number;

            if (kind == ROW_AREA) {
                text.setFont(Graphics.FONT_XTINY);
                text.setColor(COLOR_AREA);
                text.setText(row[1] as Lang.String);
                text.setLocation(left, top);
                text.setSize(right - left, ROW_HEIGHT);
                continue;
            }

            var label = _rowLabel(kind, row);
            var value = _rowValue(kind, row);
            var span = right - left;
            var valueWidth = VALUE_WIDTH;
            if (span < VALUE_WIDTH + 80) {
                valueWidth = Math.floor(span * 0.35);
            }
            var labelWidth = span - valueWidth - 4;
            if (labelWidth < 20) {
                labelWidth = 20;
            }
            label = _truncate(dc, label, Graphics.FONT_SMALL, labelWidth);
            text.setFont(Graphics.FONT_SMALL);
            text.setColor(COLOR_TEXT);
            text.setText(label);
            text.setLocation(left, top);
            text.setSize(labelWidth, ROW_HEIGHT);

            if (value != "") {
                var valueText = _truncate(dc, value, Graphics.FONT_SMALL, valueWidth);
                var width = dc.getTextWidthInPixels(valueText, Graphics.FONT_SMALL);
                dc.setColor(COLOR_DIM, Graphics.COLOR_TRANSPARENT);
                dc.drawText(right - width, top, Graphics.FONT_SMALL, valueText, Graphics.TEXT_JUSTIFY_LEFT);
            }
        }
    }

    //! The text of the status bar.
    private function _footerText() as Lang.String {
        if (mError != null && mError != "") {
            return mError;
        }
        var pages = 1;
        if (mRowsPerPage > 0) {
            pages = Math.ceil(mRows.size() * 1.0 / mRowsPerPage);
        }
        if (pages < 1) {
            pages = 1;
        }
        var page = 1;
        if (mRowsPerPage > 0) {
            page = Math.floor(mTop * 1.0 / mRowsPerPage) + 1;
        }
        var text = page.toString() + "/" + pages.toString();
        if (mStatus != null && mStatus != "") {
            text = text + "  " + mStatus;
        }
        return text;
    }

    //! Place the title bar.
    private function _setHeader(dc as Dc, title as Lang.String) as Void {
        if (mHeader == null) {
            return;
        }
        mHeader.setJustification(Graphics.TEXT_JUSTIFY_LEFT);
        mHeader.setFont(Graphics.FONT_SMALL);
        mHeader.setColor(COLOR_TEXT);
        mHeader.setText(title);
        var width = dc.getTextWidthInPixels(title, Graphics.FONT_SMALL);
        mHeader.setLocation(mCentre - Math.floor(width / 2.0), 3);
        mHeader.setSize(mWidth, HEADER_HEIGHT);
    }

    //! Place the status bar.
    private function _setFooter(dc as Dc, text as Lang.String) as Void {
        if (mFooter == null) {
            return;
        }
        mFooter.setJustification(Graphics.TEXT_JUSTIFY_LEFT);
        mFooter.setFont(Graphics.FONT_XTINY);
        mFooter.setColor(COLOR_DIM);
        mFooter.setText(text);
        var width = dc.getTextWidthInPixels(text, Graphics.FONT_XTINY);
        mFooter.setLocation(mCentre - Math.floor(width / 2.0), mHeight - FOOTER_HEIGHT - 1);
        mFooter.setSize(mWidth, FOOTER_HEIGHT);
    }

    //! Shorten a string until it fits into a width.
    private function _truncate(dc as Dc, text as Lang.String, font as Lang.FontType, maxWidth as Lang.Number) as Lang.String {
        if (text == null || text == "") {
            return "";
        }
        if (maxWidth <= 0) {
            return "";
        }
        if (dc.getTextWidthInPixels(text, font) <= maxWidth) {
            return text;
        }
        var result = text;
        while (result.length() > 1 && dc.getTextWidthInPixels(result + "...", font) > maxWidth) {
            result = result.substring(0, result.length() - 1);
        }
        return result + "...";
    }

    // -- the detail screen -------------------------------------------------

    //! Draw the detail screen.
    private function _renderDetail(dc as Dc) as Void {
        var band = _safeBand();
        var bandTop = band[0] as Lang.Number;
        var bandBottom = band[1] as Lang.Number;
        var bandHeight = bandBottom - bandTop;
        var contentWidth = bandHeight;
        var contentLeft = mCentre - Math.floor(contentWidth / 2.0);
        if (!mRound) {
            contentWidth = mWidth - 2 * MARGIN;
            contentLeft = MARGIN;
        }

        var title = "";
        var subtitle = "";
        var state = "";
        var value = "";
        var body = "";
        if (mDetailKind == DETAIL_NOTIFICATION) {
            var notification = mStore.notificationAt(mSelection);
            if (notification != null) {
                title = Values.string(notification[EntityStore.NOTIF_TITLE]);
                subtitle = Values.string(notification[EntityStore.NOTIF_BODY]);
                body = "";
            }
        } else {
            title = mStore.nameAt(mSelection);
            if (title == null || title == "") {
                title = App.loadResource(Rez.Strings.UnnamedEntity) as String;
            }
            var area = mStore.areaNameAt(mSelection);
            var domain = mStore.domainAt(mSelection);
            subtitle = area == null ? domain : area + "  " + domain;
            state = mStore.stateAt(mSelection);
            var raw = mStore.valueAt(mSelection);
            if (raw != null) {
                value = Values.format(raw);
            }
            body = mStore.entityIdAt(mSelection);
        }
        if (title == null) {
            title = "";
        }
        if (subtitle == null) {
            subtitle = "";
        }
        if (state == null) {
            state = "";
        }

        _setHeader(dc, App.loadResource(Rez.Strings.Status) as String);
        _setFooter(dc, _footerText());

        var y = bandTop;
        _placeText(dc, mTitle, title, Graphics.FONT_MEDIUM, COLOR_TEXT, contentLeft, y, contentWidth, 26);
        y += 28;
        _placeText(dc, mSubtitle, subtitle, Graphics.FONT_XTINY, COLOR_DIM, contentLeft, y, contentWidth, 18);
        y += 20;
        _placeText(dc, mState, state, Graphics.FONT_LARGE, COLOR_TEXT, contentLeft, y, contentWidth, 30);
        y += 32;
        _placeText(dc, mValue, value, Graphics.FONT_SMALL, COLOR_DIM, contentLeft, y, contentWidth, 20);
        y += 22;

        // The buttons sit at the bottom of the safe band.
        var count = mActions.size();
        var cols = contentWidth >= 220 ? 2 : 1;
        var rows = Math.ceil(count * 1.0 / cols);
        var buttonWidth = Math.floor((contentWidth - (cols - 1) * BUTTON_GAP) / cols);
        if (buttonWidth < 40) {
            buttonWidth = 40;
        }
        var buttonsTop = bandBottom - rows * BUTTON_HEIGHT - (rows - 1) * BUTTON_GAP;
        if (buttonsTop < y) {
            buttonsTop = y;
        }

        for (var i = 0; i < MAX_ACTIONS; i++) {
            var button = mButtons[i] as Ui.Button;
            var label = mButtonLabels[i] as Ui.Text;
            if (i >= count) {
                button.setVisible(false);
                label.setVisible(false);
                continue;
            }
            button.setVisible(true);
            label.setVisible(true);
            var col = i % cols;
            var row = Math.floor(i * 1.0 / cols);
            var x = contentLeft + col * (buttonWidth + BUTTON_GAP);
            var by = buttonsTop + row * (BUTTON_HEIGHT + BUTTON_GAP);
            button.setLocation(x, by);
            button.setSize(buttonWidth, BUTTON_HEIGHT);
            var action = mActions[i] as Lang.Dictionary;
            var actionLabel = action.get("label") as Lang.String;
            if (actionLabel == null) {
                actionLabel = "";
            }
            var textWidth = dc.getTextWidthInPixels(actionLabel, Graphics.FONT_XTINY);
            label.setText(actionLabel);
            label.setLocation(x + Math.floor((buttonWidth - textWidth) / 2.0), by + 9);
            label.setSize(buttonWidth, BUTTON_HEIGHT);
            label.setColor(COLOR_TEXT);
            if (i == mActionIndex) {
                button.setState(:stateSelected);
            } else {
                button.setState(:stateDefault);
            }
        }

        if (mBody != null) {
            mBody.setVisible(body != "");
            mBody.setText(body);
            mBody.setLocation(contentLeft, y);
            mBody.setSize(contentWidth, buttonsTop - y - 4);
        }
    }

    //! Place one line of text.
    private function _placeText(
        dc as Dc,
        target as Ui.Text?,
        text as Lang.String,
        font as Lang.FontType,
        color as Lang.Number,
        left as Lang.Number,
        top as Lang.Number,
        width as Lang.Number,
        height as Lang.Number
    ) as Void {
        if (target == null) {
            return;
        }
        target.setVisible(true);
        target.setJustification(Graphics.TEXT_JUSTIFY_LEFT);
        target.setFont(font);
        target.setColor(color);
        target.setText(text);
        target.setLocation(left, top);
        target.setSize(width, height);
    }

    //! Build the actions of the detail screen.
    private function _buildActions() as Void {
        mActions = [];
        mActionIndex = 0;
        if (mDetailKind == DETAIL_NOTIFICATION) {
            var notification = mStore.notificationAt(mSelection);
            if (notification == null) {
                return;
            }
            var rows = Values.array(notification[EntityStore.NOTIF_ACTIONS]);
            if (rows == null) {
                return;
            }
            for (var i = 0; i < rows.size() && mActions.size() < MAX_ACTIONS; i++) {
                var action = rows[i] as Lang.Array;
                if (action == null || action.size() < 2) {
                    continue;
                }
                mActions.add({
                    "label" => Values.string(action[1]),
                    "cmd" => "ack",
                    "action" => Values.string(action[0]),
                    "data" => null
                });
            }
            return;
        }

        var index = mSelection;
        var flags = mStore.flagsAt(index);
        var domain = mStore.domainAt(index);
        var state = mStore.stateAt(index);
        if (flags & EntityStore.FLAG_TOGGLE) {
            mActions.add({
                "label" => App.loadResource(Rez.Strings.Toggle) as String,
                "cmd" => "toggle",
                "action" => null,
                "data" => null
            });
        }
        if (flags & EntityStore.FLAG_OPEN_CLOSE) {
            mActions.add({
                "label" => App.loadResource(Rez.Strings.Open) as String,
                "cmd" => "open",
                "action" => null,
                "data" => null
            });
            mActions.add({
                "label" => App.loadResource(Rez.Strings.Close) as String,
                "cmd" => "close",
                "action" => null,
                "data" => null
            });
        }
        var value = Values.double(mStore.valueAt(index));
        if (value != null) {
            if (flags & EntityStore.FLAG_BRIGHTNESS) {
                var percent = Math.floor(value * 100.0 / 255.0);
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Brighter) as String,
                    "cmd" => "set_level",
                    "action" => null,
                    "data" => { "value" => _clamp(percent + 10, 0, 100) }
                });
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Dimmer) as String,
                    "cmd" => "set_level",
                    "action" => null,
                    "data" => { "value" => _clamp(percent - 10, 0, 100) }
                });
            } else if (flags & EntityStore.FLAG_LEVEL) {
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Increase) as String,
                    "cmd" => "set_level",
                    "action" => null,
                    "data" => { "value" => _clamp(value.toNumber() + 10, 0, 100) }
                });
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Decrease) as String,
                    "cmd" => "set_level",
                    "action" => null,
                    "data" => { "value" => _clamp(value.toNumber() - 10, 0, 100) }
                });
            }
            if (flags & EntityStore.FLAG_SETPOINT) {
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Increase) as String,
                    "cmd" => "set_value",
                    "action" => null,
                    "data" => { "value" => value.toNumber() + 1 }
                });
                mActions.add({
                    "label" => App.loadResource(Rez.Strings.Decrease) as String,
                    "cmd" => "set_value",
                    "action" => null,
                    "data" => { "value" => value.toNumber() - 1 }
                });
            }
        }
        if (mActions.size() == 0 && domain != null && domain != "") {
            mActions.add({
                "label" => App.loadResource(Rez.Strings.Refresh) as String,
                "cmd" => "toggle",
                "action" => null,
                "data" => null
            });
        }
        while (mActions.size() > MAX_ACTIONS) {
            mActions.remove(mActions.size() - 1);
        }
    }

    //! Keep a number inside a range.
    private function _clamp(value as Lang.Number, low as Lang.Number, high as Lang.Number) as Lang.Number {
        if (value < low) {
            return low;
        }
        if (value > high) {
            return high;
        }
        return value;
    }

    //! Run the selected action.
    private function _runAction() as Void {
        if (mActionIndex < 0 || mActionIndex >= mActions.size()) {
            return;
        }
        var action = mActions[mActionIndex] as Lang.Dictionary;
        var cmd = action.get("cmd") as Lang.String;
        mLastActionAt = Time.now().value();
        if (cmd == "ack") {
            var notification = mStore.notificationAt(mSelection);
            if (notification == null) {
                return;
            }
            var notificationId = Values.string(notification[EntityStore.NOTIF_ID]);
            mClient.ackNotification(notificationId, action.get("action"), method(:onCommand));
            mStore.removeNotification(notificationId);
            _rebuildRows();
            _back();
            return;
        }
        var entityId = mStore.entityIdAt(mSelection);
        mClient.sendCommand(cmd, entityId, Values.dictionary(action.get("data")), method(:onCommand));
    }

    //! The bridge answered a command.
    private function onCommand(code as Lang.Number, data as Lang.Dictionary?) as Void {
        if (code == 200 && data != null) {
            var ok = Values.boolean(Values.member(data, "ok"));
            var message = Values.memberString(data, "message", "");
            if (ok) {
                mError = "";
                mStatus = message;
            } else {
                mError = message;
            }
        } else {
            mError = HttpClient.describe(code);
        }
        // The state of the entity may have changed, ask for it again.
        mLastPoll = 0;
        _refresh();
    }

    // -- input -------------------------------------------------------------

    //! A hardware key was pressed.
    //!
    //! @param key One of the WatchUi.KEY_* constants.
    //! @return True when the key was used.
    function handleKey(key as Lang.Number) as Lang.Boolean {
        if (key == null) {
            return false;
        }
        if (mScreen == SCREEN_DETAIL) {
            if (key == Ui.KEY_ESC || key == Ui.KEY_LAP) {
                _back();
                return true;
            }
            if (key == Ui.KEY_UP) {
                _moveAction(-1);
                return true;
            }
            if (key == Ui.KEY_DOWN) {
                _moveAction(1);
                return true;
            }
            if (key == Ui.KEY_ENTER || key == Ui.KEY_START) {
                _runAction();
                return true;
            }
            return false;
        }
        if (key == Ui.KEY_ESC || key == Ui.KEY_LAP) {
            if (mScreen == SCREEN_INBOX) {
                _showScreen(SCREEN_LIST);
                return true;
            }
            // The list is the first screen, let the system close the app.
            return false;
        }
        if (key == Ui.KEY_UP) {
            _moveSelection(-1);
            return true;
        }
        if (key == Ui.KEY_DOWN) {
            _moveSelection(1);
            return true;
        }
        if (key == Ui.KEY_ENTER || key == Ui.KEY_START) {
            _openSelection();
            return true;
        }
        return false;
    }

    //! The screen was tapped.
    //!
    //! @param x The horizontal position of the tap.
    //! @param y The vertical position of the tap.
    //! @return True when the tap was used.
    function handleTap(x as Lang.Number, y as Lang.Number) as Lang.Boolean {
        if (x == null || y == null) {
            return false;
        }
        if (mScreen == SCREEN_DETAIL) {
            for (var i = 0; i < mButtons.size(); i++) {
                var button = mButtons[i] as Ui.Button;
                if (!button.isVisible) {
                    continue;
                }
                if (x >= button.locX && x <= button.locX + button.width &&
                    y >= button.locY && y <= button.locY + button.height) {
                    mActionIndex = i;
                    _runAction();
                    return true;
                }
            }
            // A tap outside the buttons does nothing, but it is consumed so
            // that it does not reach the system.
            return true;
        }
        if (y < mBodyTop || y > mBodyBottom) {
            return false;
        }
        var slot = Math.floor((y - mBodyTop) * 1.0 / ROW_HEIGHT);
        if (slot < 0 || slot >= mSlotCount) {
            return false;
        }
        var rowIndex = mTop + slot;
        if (rowIndex >= mRows.size()) {
            return false;
        }
        var row = mRows[rowIndex] as Lang.Array;
        var kind = row[0] as Lang.Number;
        if (kind == ROW_AREA) {
            return true;
        }
        mSelection = row[1] as Lang.Number;
        _openSelection();
        return true;
    }

    //! The screen was swiped.
    //!
    //! @param direction One of the WatchUi.SWIPE_* constants.
    //! @return True when the swipe was used.
    function handleSwipe(direction as Lang.Number) as Lang.Boolean {
        if (direction == null || mScreen == SCREEN_DETAIL) {
            return false;
        }
        if (direction == Ui.SWIPE_UP) {
            _page(1);
            return true;
        }
        if (direction == Ui.SWIPE_DOWN) {
            _page(-1);
            return true;
        }
        if (direction == Ui.SWIPE_LEFT && mScreen == SCREEN_LIST) {
            _showScreen(SCREEN_INBOX);
            return true;
        }
        if (direction == Ui.SWIPE_RIGHT && mScreen == SCREEN_INBOX) {
            _showScreen(SCREEN_LIST);
            return true;
        }
        return false;
    }

    //! Switch to another screen.
    private function _showScreen(screen as Lang.Number) as Void {
        mScreen = screen;
        mSelection = 0;
        mTop = 0;
        mError = "";
        _rebuildRows();
    }

    //! A selectable was activated.
    //!
    //! The buttons of the detail screen carry the index of their action.
    function handleSelectable(event as Ui.SelectableEvent) as Lang.Boolean {
        if (event == null) {
            return false;
        }
        var selectable = event.getInstance() as Ui.Selectable;
        if (selectable == null) {
            return false;
        }
        var index = Values.number(selectable.identifier);
        if (index == null) {
            return false;
        }
        if (_debounced()) {
            // The tap was already handled by the touch handler.
            return true;
        }
        mActionIndex = index;
        _runAction();
        return true;
    }

    //! True when the last action happened less than a second ago.
    private function _debounced() as Lang.Boolean {
        if (mLastActionAt < 0) {
            return false;
        }
        return (Time.now().value() - mLastActionAt) < 1;
    }

    //! Move the selection up or down.
    private function _moveSelection(delta as Lang.Number) as Void {
        var limit = _selectionCount();
        if (limit <= 0) {
            return;
        }
        mSelection += delta;
        if (mSelection < 0) {
            mSelection = 0;
        }
        if (mSelection >= limit) {
            mSelection = limit - 1;
        }
        _ensureVisible();
    }

    //! Move the action selection up or down.
    private function _moveAction(delta as Lang.Number) as Void {
        if (mActions.size() == 0) {
            return;
        }
        mActionIndex += delta;
        if (mActionIndex < 0) {
            mActionIndex = mActions.size() - 1;
        }
        if (mActionIndex >= mActions.size()) {
            mActionIndex = 0;
        }
    }

    //! The number of items that can be selected.
    private function _selectionCount() as Lang.Number {
        if (mScreen == SCREEN_INBOX) {
            return mStore.notificationCount();
        }
        return mStore.size();
    }

    //! The row that holds the current selection.
    private function _rowOfSelection() as Lang.Number {
        var kind = mScreen == SCREEN_INBOX ? ROW_NOTIFICATION : ROW_ENTITY;
        for (var i = 0; i < mRows.size(); i++) {
            var row = mRows[i] as Lang.Array;
            if ((row[0] as Lang.Number) != kind) {
                continue;
            }
            if ((row[1] as Lang.Number) == mSelection) {
                return i;
            }
        }
        return -1;
    }

    //! Scroll so that the selection is visible.
    private function _ensureVisible() as Void {
        var rowIndex = _rowOfSelection();
        if (rowIndex < 0) {
            return;
        }
        if (rowIndex < mTop) {
            mTop = rowIndex;
        } else if (rowIndex >= mTop + mRowsPerPage) {
            mTop = rowIndex - mRowsPerPage + 1;
        }
        if (mTop < 0) {
            mTop = 0;
        }
    }

    //! Move one page up or down.
    private function _page(delta as Lang.Number) as Void {
        var last = mRows.size() - mRowsPerPage;
        if (last < 0) {
            last = 0;
        }
        mTop += delta * mRowsPerPage;
        if (mTop < 0) {
            mTop = 0;
        }
        if (mTop > last) {
            mTop = last;
        }
    }

    //! Open the detail screen of the current selection.
    private function _openSelection() as Void {
        if (mScreen == SCREEN_INBOX) {
            if (mSelection < 0 || mSelection >= mStore.notificationCount()) {
                return;
            }
            mDetailKind = DETAIL_NOTIFICATION;
        } else {
            if (mSelection < 0 || mSelection >= mStore.size()) {
                return;
            }
            mDetailKind = DETAIL_ENTITY;
        }
        mReturnScreen = mScreen;
        mScreen = SCREEN_DETAIL;
        mError = "";
        _buildActions();
    }

    //! Leave the detail screen.
    private function _back() as Void {
        mScreen = mReturnScreen;
        mActions = [];
        _rebuildRows();
    }
}
