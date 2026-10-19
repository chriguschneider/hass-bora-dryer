"""Polling and parsing of status.html / info.html, and the filter reminder."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bora_dryer.const import (
    CONF_FILTER_DUE_HOURS,
    CONF_FILTER_NOTIFY,
)
from custom_components.bora_dryer.coordinator import (
    FILTER_NOTIFICATION_ID,
    BoraDataUpdateCoordinator,
)

from .conftest import DEVICE_ID, HOST, MODEL, load_fixture

EXPECTED = {
    "temperature": 21.5,
    "humidity": 48,
    "operation_state": "Standby",
    "filter_hours": 123,
    "filter_minutes": 45,
    # The parser drops the leading "V" of "V1.0.006".
    "firmware_version": "1.0.006",
    "device_id": DEVICE_ID,
    "model": MODEL,
}


def _info_with_filter(hours: int) -> str:
    return load_fixture("info.html").replace("Filter 123:45", f"Filter {hours}:00")


def _notifications(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    key = f"{FILTER_NOTIFICATION_ID}_{entry.entry_id}"
    return {
        k: v
        for k, v in persistent_notification._async_get_or_create_notifications(
            hass
        ).items()
        if k == key
    }


async def _poll(
    hass: HomeAssistant, entry: MockConfigEntry
) -> BoraDataUpdateCoordinator:
    coordinator = BoraDataUpdateCoordinator(hass, entry)
    await coordinator.async_refresh()
    return coordinator


async def test_parses_every_field(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    coordinator = await _poll(hass, config_entry)
    assert coordinator.last_update_success
    assert coordinator.data == EXPECTED
    # Both pages are read from the configured host, nothing else.
    urls = sorted(str(call[1]) for call in mock_device.mock_calls)
    assert urls == [f"http://{HOST}/info.html", f"http://{HOST}/status.html"]


async def test_negative_temperature_and_drying_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    status = (
        load_fixture("status.html")
        .replace("21.5 °C", "-2.0 °C")
        .replace("Standby<br>", "Drying<br>")
    )
    switch_device(True, status=status)
    coordinator = await _poll(hass, config_entry)
    assert coordinator.data["temperature"] == -2.0
    assert coordinator.data["operation_state"] == "Drying"


async def test_unparsable_pages_give_none_not_an_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    """A page without the markers is a successful poll with empty fields."""
    switch_device(True, status="<html></html>", info="<html></html>")
    coordinator = await _poll(hass, config_entry)
    assert coordinator.last_update_success
    assert set(coordinator.data) == set(EXPECTED)
    assert all(value is None for value in coordinator.data.values())


async def test_unreachable_device_fails_the_update(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(False)
    coordinator = BoraDataUpdateCoordinator(hass, config_entry)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_filter_reminder_fires_once_on_the_rising_edge(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(True, info=_info_with_filter(279))
    coordinator = await _poll(hass, config_entry)
    assert not _notifications(hass, config_entry)

    switch_device(True, info=_info_with_filter(280))  # default threshold
    await coordinator.async_refresh()
    assert len(_notifications(hass, config_entry)) == 1

    # Dismissed by the user: later polls above the threshold do not re-nag.
    persistent_notification.async_dismiss(
        hass, f"{FILTER_NOTIFICATION_ID}_{config_entry.entry_id}"
    )
    switch_device(True, info=_info_with_filter(281))
    await coordinator.async_refresh()
    assert not _notifications(hass, config_entry)


async def test_filter_reset_on_device_clears_the_reminder(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(True, info=_info_with_filter(290))
    coordinator = await _poll(hass, config_entry)
    assert len(_notifications(hass, config_entry)) == 1

    switch_device(True, info=_info_with_filter(0))
    await coordinator.async_refresh()
    assert not _notifications(hass, config_entry)


async def test_filter_reminder_follows_the_options(
    hass: HomeAssistant,
    switch_device: Callable[..., None],
) -> None:
    entry = MockConfigEntry(
        domain="bora_dryer",
        unique_id=DEVICE_ID,
        data={"host": HOST},
        options={CONF_FILTER_DUE_HOURS: 150, CONF_FILTER_NOTIFY: True},
    )
    entry.add_to_hass(hass)
    switch_device(True, info=_info_with_filter(150))
    await _poll(hass, entry)
    assert len(_notifications(hass, entry)) == 1

    muted = MockConfigEntry(
        domain="bora_dryer",
        unique_id="e5f6a7b8",
        data={"host": HOST},
        options={CONF_FILTER_DUE_HOURS: 150, CONF_FILTER_NOTIFY: False},
    )
    muted.add_to_hass(hass)
    await _poll(hass, muted)
    assert not _notifications(hass, muted)
