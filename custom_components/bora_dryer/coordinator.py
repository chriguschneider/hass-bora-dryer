"""Data update coordinator for the BORA dryer."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FILTER_DUE_HOURS,
    DEFAULT_FILTER_DUE_HOURS,
    DOMAIN,
    HTTP_TIMEOUT,
    SCAN_INTERVAL,
)

FILTER_ISSUE_ID = "filter_maintenance_due"

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

        self._update_filter_issue(data)
        return data

    def _update_filter_issue(self, data: dict[str, Any]) -> None:
        """Raise / clear the HA repair issue for filter maintenance."""
        hours = data.get("filter_hours")
        if hours is None:
            return
        threshold = self.entry.options.get(
            CONF_FILTER_DUE_HOURS, DEFAULT_FILTER_DUE_HOURS
        )
        issue_id = f"{FILTER_ISSUE_ID}_{self.entry.entry_id}"
        if hours >= threshold:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=FILTER_ISSUE_ID,
                translation_placeholders={
                    "hours": str(hours),
                    "threshold": str(threshold),
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
