"""Button platform for the BORA dryer.

Exposes a 'Set clock' button that pushes the current Home Assistant local time
to the BORA via the same /date.html endpoint the device's web UI uses. This is
the only documented write operation the device's HTTP server accepts.
"""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode

import aiohttp

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, HTTP_TIMEOUT
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoraSetClockButton(coordinator)])


class BoraSetClockButton(BoraEntity, ButtonEntity):
    """Push HA local time to the BORA's clock."""

    _attr_translation_key = "set_clock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-edit-outline"

    def __init__(self, coordinator: BoraDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_set_clock"

    async def async_press(self) -> None:
        host = self.coordinator.entry.data["host"]
        now = dt_util.now()
        # Same parameter shape the device's own JS produces in /date.html.
        params = {
            "Z1": str(now.day),
            "Z2": str(now.month),
            "Z3": str(now.year - 2000),
            "P": "0",
            "Z4": now.strftime("%H:%M:%S"),
            "Z5": "Save",
        }
        url = f"http://{host}/date.html?{urlencode(params)}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as resp:
                resp.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to push clock to BORA at %s: %s", host, err)
            raise
