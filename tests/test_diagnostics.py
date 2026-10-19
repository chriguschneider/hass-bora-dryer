"""Diagnostics download: redacted entry, parsed data, scrubbed raw pages."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bora_dryer.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import DEVICE_ID, HOST, load_fixture

REDACTED = "**REDACTED**"


async def test_diagnostics_redacts(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    info = (
        load_fixture("info.html")
        + "<p>ip 198.51.100.7 mac AA:BB:CC:DD:EE:FF S0=MyNet&S1=secret"
        + " ssid Bora 4xx-0a1b2c3d</p>"
    )
    switch_device(True, info=info)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert {"entry", "data", "raw"} <= result.keys()
    assert result["entry"]["data"]["host"] == REDACTED
    assert result["entry"]["unique_id"] == REDACTED
    assert result["data"]["device_id"] == REDACTED
    raw = result["raw"]["info.html"]
    for leaked in ("198.51.100.7", "AA:BB:CC:DD:EE:FF", "secret", "MyNet", DEVICE_ID):
        assert leaked not in raw
    assert "Filter 123:45" in raw
    assert HOST not in str(result)
    assert "status.html" in result["raw"]


async def test_diagnostics_device_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(False)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["raw"] == {}
    assert result["entry"]["data"]["host"] == REDACTED
