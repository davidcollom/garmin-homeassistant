"""Notification platform for the Garmin Home Assistant integration.

Registers the ``notify.garmin_homeassistant`` service.  Notifications are
queued on the bridge and delivered to the watch on its next poll.  When a
phone notification service is configured the message is mirrored there too, so
the Garmin Connect mobile app can push it to the watch immediately.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import BridgeClient
from .const import (
    CONF_PHONE_NOTIFY_SERVICE,
    DATA_CLIENT,
    DEFAULT_NOTIFY_TITLE,
)
from .helpers import split_service_name

_LOGGER = logging.getLogger(__name__)

#: Name used for the ``notify.<name>`` service.  Slugified by Home Assistant
#: into ``notify.garmin_homeassistant``.
NOTIFY_SERVICE_NAME = "Garmin Homeassistant"


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> GarminNotificationService | None:
    """Return the notification service for the bridge."""
    if not discovery_info:
        return None
    client = discovery_info.get(DATA_CLIENT)
    if client is None:
        _LOGGER.error("No bridge client was supplied to the notify platform")
        return None
    return GarminNotificationService(discovery_info)


class GarminNotificationService(BaseNotificationService):
    """Send notifications to the Garmin watches."""

    def __init__(self, discovery_info: DiscoveryInfoType) -> None:
        """Initialise the service."""
        self._client: BridgeClient = discovery_info[DATA_CLIENT]
        self._phone_service: str = str(discovery_info.get(CONF_PHONE_NOTIFY_SERVICE) or "")

    async def async_send_message(self, message: str, **kwargs: Any) -> None:
        """Queue a message for the watches."""
        title = kwargs.get(ATTR_TITLE) or DEFAULT_NOTIFY_TITLE
        data = kwargs.get(ATTR_DATA) or {}
        targets = kwargs.get(ATTR_TARGET) or []

        priority = str(data.get("priority") or "normal")
        actions = data.get("actions") or []
        entity_id = data.get("entity_id")

        try:
            await self._client.async_notify(
                title=str(title),
                message=str(message),
                priority=priority,
                actions=list(actions),
                entity_id=entity_id,
                watch_ids=list(targets) if targets else None,
            )
        except Exception as err:  # noqa: BLE001 - surfaced to the caller
            _LOGGER.error("Could not queue the notification: %s", err)
            raise

        await self._async_mirror_to_phone(message, title)

    async def _async_mirror_to_phone(self, message: str, title: str) -> None:
        """Mirror the notification to the paired phone, if configured."""
        if not self._phone_service or self.hass is None:
            return
        domain, service = split_service_name(self._phone_service)
        try:
            await self.hass.services.async_call(
                domain,
                service,
                {ATTR_MESSAGE: message, ATTR_TITLE: title},
                blocking=False,
            )
        except Exception as err:  # noqa: BLE001 - best effort delivery
            _LOGGER.warning("Could not mirror the notification to %s: %s", self._phone_service, err)


@callback
def async_register_phone_service(hass: HomeAssistant, service: str) -> None:
    """Update the phone notification service used for mirroring."""
    for notify_service in _async_notify_services(hass):
        notify_service._phone_service = service  # noqa: SLF001 - internal update


def _async_notify_services(hass: HomeAssistant) -> list[GarminNotificationService]:
    """Return the registered Garmin notify services."""
    from homeassistant.components.notify.legacy import NOTIFY_SERVICES

    services = hass.data.get(NOTIFY_SERVICES, {})
    result: list[GarminNotificationService] = []
    for platform_services in services.values():
        for service in platform_services:
            if isinstance(service, GarminNotificationService):
                result.append(service)
    return result
