//
// Input delegate for the Garmin Home Assistant watch application.
//
// The delegate translates the hardware keys and the touch gestures into the
// calls the view understands.  Keeping the two apart means the view can be
// exercised without a physical device.
//
// The two target families use different keys:
//
//     Venu 4     KEY_ENTER selects, KEY_ESC goes back
//     Edge 1040  KEY_START selects, KEY_LAP goes back
//
// so every key is accepted in both roles.
//
// Licensed under the MIT licence, see LICENSE in the repository root.
//
import Toybox.Lang;
using Toybox.WatchUi as Ui;

class MainDelegate extends Ui.InputDelegate {

    private var mView as MainView;

    function initialize(view as MainView) {
        Ui.InputDelegate.initialize();
        mView = view;
    }

    //! A hardware key was pressed and released.
    function onKey(keyEvent as Ui.KeyEvent) as Lang.Boolean {
        if (mView == null || keyEvent == null) {
            return false;
        }
        return mView.handleKey(keyEvent.getKey());
    }

    //! The screen was tapped.
    function onTap(clickEvent as Ui.ClickEvent) as Lang.Boolean {
        if (mView == null || clickEvent == null) {
            return false;
        }
        var coordinates = clickEvent.getCoordinates();
        if (coordinates == null || coordinates.size() < 2) {
            return false;
        }
        return mView.handleTap(coordinates[0] as Lang.Number, coordinates[1] as Lang.Number);
    }

    //! The screen was swiped.
    function onSwipe(swipeEvent as Ui.SwipeEvent) as Lang.Boolean {
        if (mView == null || swipeEvent == null) {
            return false;
        }
        return mView.handleSwipe(swipeEvent.getDirection());
    }

    //! A selectable -- one of the action buttons -- was activated.
    function onSelectable(selectableEvent as Ui.SelectableEvent) as Lang.Boolean {
        if (mView == null || selectableEvent == null) {
            return false;
        }
        return mView.handleSelectable(selectableEvent);
    }
}
