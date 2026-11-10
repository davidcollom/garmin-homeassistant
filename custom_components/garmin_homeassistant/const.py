"""Constants for the Garmin Home Assistant integration."""

from __future__ import annotations

DOMAIN = "garmin_homeassistant"

#: Configuration keys.
CONF_BRIDGE_URL = "bridge_url"
CONF_BRIDGE_TOKEN = "bridge_token"
CONF_EXPOSED_ENTITIES = "exposed_entities"
CONF_BLOCKED_ENTITIES = "blocked_entities"
CONF_PHONE_NOTIFY_SERVICE = "phone_notify_service"
CONF_CREATE_MIRROR_SWITCHES = "create_mirror_switches"
CONF_SCAN_INTERVAL = "scan_interval"

#: Defaults.
DEFAULT_BRIDGE_URL = "http://garmin-bridge:8099"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NOTIFY_TITLE = "Home Assistant"

#: Service names.
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_RUN_COMMAND = "run_command"
SERVICE_SET_EXPOSED_ENTITIES = "set_exposed_entities"
SERVICE_REFRESH = "refresh"

#: Event fired on the bus when a watch acknowledges a notification action.
EVENT_WATCH_ACTION = "garmin_homeassistant_watch_action"

#: Keys used to pass data to the notify platform.
DATA_CLIENT = "client"
DATA_NOTIFY_NAME = "notify_name"

#: Attribute keys used on entities.
ATTR_WATCH_ID = "watch_id"
ATTR_ENTITY_ID = "entity_id"
ATTR_ACTION = "action"
ATTR_BATTERY = "battery"
ATTR_STEPS = "steps"
ATTR_HEART_RATE = "heart_rate"
ATTR_LAST_SEEN = "last_seen"

#: Bit flags of the compact entity format of the bridge.  They have to match
#: the ``EntityFlags`` of the bridge and the ``FLAG_*`` constants of the watch
#: application.
FLAG_TOGGLE = 1
FLAG_BRIGHTNESS = 2
FLAG_LEVEL = 4
FLAG_OPEN_CLOSE = 8
FLAG_SETPOINT = 16
FLAG_PINNED = 32
FLAG_PERCENT = 64
