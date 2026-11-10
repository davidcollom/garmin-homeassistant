"""Small helpers shared by the modules of the integration."""

from __future__ import annotations

#: The domain used for notification services.
NOTIFY_DOMAIN = "notify"


def split_service_name(service: str) -> tuple[str, str]:
    """Split a service name into its domain and the service name.

    ``notify.mobile_app_iphone`` becomes ``("notify", "mobile_app_iphone")``.
    A name without a domain is assumed to be a notification service.
    """
    domain, _, name = service.partition(".")
    if not name:
        return NOTIFY_DOMAIN, domain
    return domain, name
