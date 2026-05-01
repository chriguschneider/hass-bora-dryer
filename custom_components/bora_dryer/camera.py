"""Camera platform for the BORA dryer.

Streams the live LCD image of the device. The BORA serves a BMP at
/LCD.BMP?<random>; we fetch it, convert to PNG (HA cameras prefer PNG/JPEG),
and cache the result for a few seconds to avoid hammering the embedded server.
"""
from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any

import aiohttp

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CAMERA_CACHE_SECONDS, DOMAIN, HTTP_TIMEOUT
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoraLcdCamera(coordinator)])


class BoraLcdCamera(BoraEntity, Camera):
    """Live mirror of the BORA touchscreen LCD as a PNG camera image."""

    _attr_translation_key = "lcd"
    _attr_icon = "mdi:monitor-screenshot"

    def __init__(self, coordinator: BoraDataUpdateCoordinator) -> None:
        BoraEntity.__init__(self, coordinator)
        Camera.__init__(self)
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_lcd"
        self._cached_png: bytes | None = None
        self._cached_at: float = 0.0
        self._lock = asyncio.Lock()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        async with self._lock:
            now = time.monotonic()
            if (
                self._cached_png is not None
                and now - self._cached_at < CAMERA_CACHE_SECONDS
            ):
                return self._cached_png

            host = self.coordinator.entry.data["host"]
            url = f"http://{host}/LCD.BMP?{int(now * 1000) % 1_000_000}"
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
                ) as resp:
                    resp.raise_for_status()
                    bmp = await resp.read()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Failed to fetch BORA LCD image: %s", err)
                return self._cached_png

            try:
                png = await self.hass.async_add_executor_job(_bmp_to_png, bmp)
            except Exception as err:  # noqa: BLE001 - Pillow may raise many subclasses
                _LOGGER.warning("Failed to convert BORA LCD BMP to PNG: %s", err)
                return self._cached_png

            self._cached_png = png
            self._cached_at = now
            return png


def _bmp_to_png(bmp: bytes) -> bytes:
    """Convert a BMP byte buffer to PNG bytes. Runs in an executor thread."""
    from PIL import Image  # imported lazily so the module loads without Pillow

    with Image.open(io.BytesIO(bmp)) as img:
        img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
