"""A switched-off BORA is normal: setup succeeds, entities hold their last value.

Covers the behaviour of v0.3.2 (setup tolerates an offline device), v0.5.1
(operation `Off` / drying off while unreachable), v0.6.0 (fallback sensors)
and v0.8.0 (last values survive a restart, the Display stays available).
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.bora_dryer.const import (
    CONF_HUMIDITY_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    DOMAIN,
)

from .conftest import DEVICE_ID, HOST


def entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    found = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{DEVICE_ID}_{key}"
    )
    assert found, f"no {platform} entity with key {key}"
    return found


def state(hass: HomeAssistant, platform: str, key: str) -> str:
    return hass.states.get(entity_id(hass, platform, key)).state


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.data[DOMAIN][entry.entry_id].async_refresh()
    await hass.async_block_till_done()


async def test_setup_succeeds_while_device_is_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(False)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED  # no ConfigEntryNotReady
    # Never seen: no value to hold yet.
    assert state(hass, "sensor", "temperature") == STATE_UNAVAILABLE
    assert state(hass, "sensor", "filter_hours") == STATE_UNAVAILABLE
    # State-like entities report the honest offline value.
    assert state(hass, "sensor", "operation_state") == "Off"
    assert state(hass, "binary_sensor", "is_drying") == STATE_OFF
    # The Display reads as idle, not unavailable.
    assert state(hass, "camera", "lcd") != STATE_UNAVAILABLE

    # Switched on: the next poll fills everything in.
    switch_device(True)
    await _refresh(hass, config_entry)
    assert state(hass, "sensor", "temperature") == "21.5"
    assert state(hass, "sensor", "operation_state") == "Standby"


async def test_entities_hold_the_last_value_when_device_goes_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(True)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "sensor", "filter_hours") == "123"

    switch_device(False)
    await _refresh(hass, config_entry)
    assert hass.data[DOMAIN][config_entry.entry_id].last_update_success is False

    assert state(hass, "sensor", "filter_hours") == "123"
    assert state(hass, "sensor", "temperature") == "21.5"
    assert state(hass, "sensor", "humidity") == "48"
    assert state(hass, "sensor", "firmware_version") == "1.0.006"
    assert state(hass, "binary_sensor", "filter_due") == STATE_OFF
    assert state(hass, "sensor", "operation_state") == "Off"
    assert state(hass, "binary_sensor", "is_drying") == STATE_OFF


async def test_last_values_survive_a_restart_with_the_device_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    sensor_id = "sensor.bora_filter_operating_hours"
    binary_id = "binary_sensor.bora_filter_maintenance_due"
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_filter_hours",
        suggested_object_id="bora_filter_operating_hours",
        config_entry=config_entry,
    )
    registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"{DEVICE_ID}_filter_due",
        suggested_object_id="bora_filter_maintenance_due",
        config_entry=config_entry,
    )
    # One call: each mock_restore_cache* call replaces the whole cache.
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(sensor_id, "290"),
                {"native_value": 290, "native_unit_of_measurement": "h"},
            ),
            (State(binary_id, STATE_ON), {}),
        ],
    )

    switch_device(False)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(sensor_id).state == "290"
    assert hass.states.get(binary_id).state == STATE_ON


async def test_fallback_sensors_report_while_device_is_off(
    hass: HomeAssistant, switch_device: Callable[..., None]
) -> None:
    hass.states.async_set("sensor.room_temperature", "19.0")
    hass.states.async_set("sensor.room_humidity", "61")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={"host": HOST, "name": "BORA"},
        options={
            CONF_TEMPERATURE_SENSOR: "sensor.room_temperature",
            CONF_HUMIDITY_SENSOR: "sensor.room_humidity",
        },
    )
    entry.add_to_hass(hass)

    switch_device(True)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Online: the BORA's own reading wins.
    assert state(hass, "sensor", "temperature") == "21.5"

    switch_device(False)
    await _refresh(hass, entry)
    assert state(hass, "sensor", "temperature") == "19.0"
    assert state(hass, "sensor", "humidity") == "61.0"

    # The external sensor is followed without waiting for a poll.
    hass.states.async_set("sensor.room_temperature", "18.5")
    await hass.async_block_till_done()
    assert state(hass, "sensor", "temperature") == "18.5"


async def test_camera_serves_no_image_while_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    switch_device: Callable[..., None],
) -> None:
    switch_device(False)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    camera = next(
        e
        for e in hass.data["camera"].entities
        if e.entity_id == entity_id(hass, "camera", "lcd")
    )
    assert await camera.async_camera_image() is None
