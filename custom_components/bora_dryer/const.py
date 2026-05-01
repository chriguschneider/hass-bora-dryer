"""Constants for the BORA dryer integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "bora_dryer"

DEFAULT_HOST = "192.168.1.100"
DEFAULT_NAME = "BORA"

SCAN_INTERVAL = timedelta(seconds=60)
HTTP_TIMEOUT = 8

# Vendor warns at 300h on the device display; surface in HA earlier.
FILTER_LIFETIME_HOURS = 300
DEFAULT_FILTER_DUE_HOURS = 280
MIN_FILTER_DUE_HOURS = 100
MAX_FILTER_DUE_HOURS = 300

# Options keys
CONF_POWER_SWITCH = "power_switch_entity_id"
CONF_FILTER_DUE_HOURS = "filter_due_hours"

# Camera caches the BMP→PNG conversion for this long.
CAMERA_CACHE_SECONDS = 5
