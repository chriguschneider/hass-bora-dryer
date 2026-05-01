"""Constants for the BORA dryer integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "bora_dryer"

DEFAULT_HOST = "192.168.1.100"
DEFAULT_NAME = "BORA"

SCAN_INTERVAL = timedelta(seconds=60)
HTTP_TIMEOUT = 8

# Roth-Kippe warns at 300h; surface in HA 20h earlier so the user has a heads-up.
FILTER_DUE_HOURS = 280
