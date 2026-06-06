"""Data update coordinator for the BORA dryer."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FILTER_DUE_HOURS,
    CONF_FILTER_NOTIFY,
    DEFAULT_FILTER_DUE_HOURS,
    DEFAULT_FILTER_NOTIFY,
    DOMAIN,
    HTTP_TIMEOUT,
    SCAN_INTERVAL,
)

# Legacy repair-issue id, kept only so __init__ can clear it on upgrade.
FILTER_ISSUE_ID = "filter_maintenance_due"
FILTER_NOTIFICATION_ID = "bora_filter"

_LOGGER = logging.getLogger(__name__)

RE_TEMPERATURE = re.compile(r"Present Temperature:\s*(-?\d+(?:\.\d+)?)\s*°C")
RE_HUMIDITY = re.compile(r"Present RH:\s*(\d+)\s*%")
RE_OPERATION = re.compile(r"Present Operation:\s*([^<\n]+?)\s*<")
RE_FILTER = re.compile(r"Filter\s*(\d+):(\d+)")
RE_FIRMWARE = re.compile(r"V(\d+\.\d+\.\d+)")
RE_DEVICE_ID = re.compile(r"V\d+\.\d+\.\d+<br>\s*([0-9a-f]{8})<br>", re.IGNORECASE)
RE_MODEL = re.compile(r"Bora\s+(\d+)")


class BoraDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the BORA HTTP status pages and parses the values."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self._host: str = entry.data["host"]
        self._session = async_get_clientsession(hass)

    async def _fetch(self, path: str) -> str:
        url = f"http://{self._host}/{path}"
        async with self._session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            raw = await resp.read()
        return raw.decode("utf-8", errors="replace")

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status_html, info_html = await asyncio.gather(
                self._fetch("status.html"),
                self._fetch("info.html"),
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error fetching BORA data: {err}") from err

        data: dict[str, Any] = {
            "temperature": None,
            "humidity": None,
            "operation_state": None,
            "filter_hours": None,
            "filter_minutes": None,
            "firmware_version": None,
            "device_id": None,
            "model": None,
        }

        if m := RE_TEMPERATURE.search(status_html):
            try:
                data["temperature"] = float(m.group(1))
            except ValueError:
                _LOGGER.debug("Failed to parse temperature from %r", m.group(1))

        if m := RE_HUMIDITY.search(status_html):
            try:
                data["humidity"] = int(m.group(1))
            except ValueError:
                _LOGGER.debug("Failed to parse humidity from %r", m.group(1))

        if m := RE_OPERATION.search(status_html):
            data["operation_state"] = m.group(1).strip()

        if m := RE_FILTER.search(info_html):
            try:
                data["filter_hours"] = int(m.group(1))
                data["filter_minutes"] = int(m.group(2))
            except ValueError:
                _LOGGER.debug("Failed to parse filter hours from %r", m.group(0))

        if m := RE_FIRMWARE.search(info_html):
            data["firmware_version"] = m.group(1)

        if m := RE_DEVICE_ID.search(info_html):
            data["device_id"] = m.group(1).lower()

        if m := RE_MODEL.search(info_html):
            data["model"] = m.group(1)

        missing = [k for k, v in data.items() if v is None]
        if missing:
            _LOGGER.debug("BORA fields not parsed this cycle: %s", missing)

        self._update_filter_notification(data)
        return data

    def _update_filter_notification(self, data: dict[str, Any]) -> None:
        """Raise / clear the persistent notification for filter maintenance.

        A filter reminder is real-world appliance maintenance, not a Home
        Assistant health problem, so it belongs in the notification panel
        rather than under Settings > System > Repairs.

        The notification is only (re)created on the rising edge — the cycle
        where filter hours first cross the threshold. Once it is showing, we do
        not recreate it on later polls, so dismissing it keeps it dismissed
        until the filter is actually reset on the device (the counter drops
        below the threshold, then climbs back over it). Dismissing the
        notification therefore acts as acknowledging the reminder. The counter
        itself cannot be reset over the LAN — only on the device display.
        """
        hours = data.get("filter_hours")
        if hours is None:
            return
        threshold = self.entry.options.get(
            CONF_FILTER_DUE_HOURS, DEFAULT_FILTER_DUE_HOURS
        )
        notify = self.entry.options.get(CONF_FILTER_NOTIFY, DEFAULT_FILTER_NOTIFY)
        notification_id = f"{FILTER_NOTIFICATION_ID}_{self.entry.entry_id}"

        if not notify or hours < threshold:
            persistent_notification.async_dismiss(self.hass, notification_id)
            return

        # hours >= threshold and notifications enabled: fire only on the rising
        # edge. A fresh coordinator (first poll, restart, options reload) has no
        # previous reading, so it nags once — acceptable.
        prev = (self.data or {}).get("filter_hours")
        if prev is None or prev < threshold:
            persistent_notification.async_create(
                self.hass,
                (
                    f"Filter operating hours: {hours} h (threshold: {threshold} h). "
                    "Clean or replace the filter, then acknowledge on the BORA's "
                    "display to reset the counter. Dismiss this notification to "
                    "silence the reminder until the next cycle."
                ),
                title=f"{self.entry.title}: filter maintenance due",
                notification_id=notification_id,
            )
