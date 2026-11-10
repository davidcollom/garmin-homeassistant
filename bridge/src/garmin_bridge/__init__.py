"""Garmin Bridge - connect Garmin Connect IQ watches to Home Assistant.

The bridge is deliberately small. It terminates watch traffic, keeps a compact
mirror of the Home Assistant entity registry, and proxies service calls back to
Home Assistant. It never talks to the Garmin cloud: watches reach it over the
internet using the paired phone as a proxy (``Toybox.Communications``).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
