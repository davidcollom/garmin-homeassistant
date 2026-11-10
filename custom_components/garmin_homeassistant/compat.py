"""Compatibility helpers for the supported Home Assistant versions.

The integration supports Home Assistant 2024.11 and newer.  A few helpers
were renamed or moved between those releases, so the imports live here to
keep the rest of the code free of version checks.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers import entity_platform

#: Callback that a platform uses to add its entities.  Home Assistant 2024.12
#: renamed ``AddEntitiesCallback`` to ``AddConfigEntryEntitiesCallback``.
AddConfigEntryEntitiesCallback: Any = getattr(
    entity_platform,
    "AddConfigEntryEntitiesCallback",
    entity_platform.AddEntitiesCallback,
)

__all__ = ["AddConfigEntryEntitiesCallback"]
