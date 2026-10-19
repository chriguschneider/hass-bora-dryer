"""Diagnostics for the BORA dryer: redacted entry, parsed data, raw pages."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACTED = "**REDACTED**"
TO_REDACT = {CONF_HOST, "device_id", "unique_id"}

# The device pages are unauthenticated; scrub anything that identifies the
# device or the user's network before the text leaves the instance.
_RE_CREDENTIALS = re.compile(r"\b(S[01]=)[^&\s\"'<>]*")
_RE_MAC = re.compile(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", re.IGNORECASE)
_RE_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Access-point SSID "Bora 4xx-<device id>".
_RE_AP_SSID = re.compile(r"(Bora\s+4xx-)[0-9a-f]+", re.IGNORECASE)


def _redact_raw(text: str, device_id: str | None) -> str:
    text = _RE_CREDENTIALS.sub(lambda m: m.group(1) + REDACTED, text)
    text = _RE_AP_SSID.sub(lambda m: m.group(1) + REDACTED, text)
    text = _RE_MAC.sub(REDACTED, text)
    text = _RE_IP.sub(REDACTED, text)
    if device_id:
        text = re.sub(re.escape(device_id), REDACTED, text, flags=re.IGNORECASE)
    return text


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = dict(coordinator.data or {})
    device_id = data.get("device_id") or entry.unique_id
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "unique_id": entry.unique_id,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "data": async_redact_data(data, TO_REDACT),
        "raw": {
            page: _redact_raw(text, device_id)
            for page, text in coordinator.last_raw.items()
        },
    }
