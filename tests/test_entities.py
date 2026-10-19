"""Entities with the device on: values, device info, button, camera, wrappers."""

from __future__ import annotations

import io
from urllib.parse import parse_qs

import pytest
from homeassistant.components.camera import async_get_image
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_platform
from homeassistant.helpers import entity_registry as er
from PIL import Image
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.bora_dryer.const import (
    CONF_ENERGY_SENSOR,
    CONF_POWER_SENSOR,
    CONF_POWER_SWITCH,
    DOMAIN,
)

from .conftest import DEVICE_ID, HOST, load_fixture


def entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    found = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{DEVICE_ID}_{key}"
    )
    assert found, f"no {platform} entity with key {key}"
    return found


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("platform", "key", "state"),
    [
        ("sensor", "temperature", "21.5"),
        ("sensor", "humidity", "48"),
        ("sensor", "operation_state", "Standby"),
        ("sensor", "filter_hours", "123"),
        ("sensor", "filter_remaining_hours", "177"),  # 300 h lifetime - 123
        ("sensor", "filter_progress_percent", "41"),  # round(123 / 300 * 100)
        ("sensor", "firmware_version", "1.0.006"),
        ("binary_sensor", "is_drying", STATE_OFF),
        ("binary_sensor", "filter_due", STATE_OFF),  # 123 < 280 default
    ],
)
async def test_entity_states(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device,
    platform: str,
    key: str,
    state: str,
) -> None:
    await _setup(hass, config_entry)
    assert hass.states.get(entity_id(hass, platform, key)).state == state


async def test_drying_and_filter_due(
    hass: HomeAssistant, config_entry: MockConfigEntry, switch_device
) -> None:
    switch_device(
        True,
        status=load_fixture("status.html").replace("Standby<br>", "Drying<br>"),
        info=load_fixture("info.html").replace("Filter 123:45", "Filter 280:00"),
    )
    await _setup(hass, config_entry)
    assert hass.states.get(entity_id(hass, "binary_sensor", "is_drying")).state == (
        STATE_ON
    )
    assert hass.states.get(entity_id(hass, "binary_sensor", "filter_due")).state == (
        STATE_ON
    )
    assert (
        hass.states.get(entity_id(hass, "sensor", "filter_remaining_hours")).state
        == "20"
    )


async def test_device_info(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    await _setup(hass, config_entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, DEVICE_ID)})
    assert device is not None
    assert device.manufacturer == "roth-kippe ag"
    assert device.model == "BORA 410"
    assert device.serial_number == DEVICE_ID
    assert device.sw_version == "1.0.006"
    assert device.configuration_url == f"http://{HOST}/"
    assert device.name == "BORA"


async def test_set_clock_button_sends_the_device_ui_request(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: AiohttpClientMocker,
    freezer,
) -> None:
    await hass.config.async_set_time_zone("Europe/Zurich")
    freezer.move_to("2026-10-19T12:30:05+00:00")  # 14:30:05 in Zurich
    mock_device.get(f"http://{HOST}/date.html", text="ok")
    await _setup(hass, config_entry)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id(hass, "button", "set_clock")},
        blocking=True,
    )
    calls = [c for c in mock_device.mock_calls if c[1].path == "/date.html"]
    assert len(calls) == 1
    query = {k: v[0] for k, v in parse_qs(calls[0][1].query_string).items()}
    assert query == {
        "Z1": "19",
        "Z2": "10",
        "Z3": "26",
        "P": "0",
        "Z4": "14:30:05",
        "Z5": "Save",
    }


def _bmp() -> bytes:
    # Generated here, not captured: the camera only needs *a* BMP to convert.
    out = io.BytesIO()
    Image.new("RGB", (4, 2), (0, 128, 255)).save(out, format="BMP")
    return out.getvalue()


async def test_camera_serves_the_lcd_as_png(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_device: AiohttpClientMocker,
) -> None:
    mock_device.get(f"http://{HOST}/LCD.BMP", content=_bmp())
    await _setup(hass, config_entry)

    image = await async_get_image(hass, entity_id(hass, "camera", "lcd"))
    assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(io.BytesIO(image.content)) as png:
        assert png.size == (4, 2)


async def test_power_switch_and_mirror_sensors_wrap_the_smart_plug(
    hass: HomeAssistant, mock_device
) -> None:
    hass.states.async_set("switch.plug", STATE_ON)
    hass.states.async_set("sensor.plug_power", "512.3")
    hass.states.async_set("sensor.plug_energy", "12.5")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        data={"host": HOST, "name": "BORA"},
        options={
            CONF_POWER_SWITCH: "switch.plug",
            CONF_POWER_SENSOR: "sensor.plug_power",
            CONF_ENERGY_SENSOR: "sensor.plug_energy",
        },
    )
    entry.add_to_hass(hass)
    await _setup(hass, entry)

    power_switch = entity_id(hass, "switch", "power")
    assert hass.states.get(power_switch).state == STATE_ON
    assert hass.states.get(entity_id(hass, "sensor", "power")).state == "512.3"
    assert hass.states.get(entity_id(hass, "sensor", "energy")).state == "12.5"

    # Follows the plug without a poll.
    hass.states.async_set("switch.plug", STATE_OFF)
    hass.states.async_set("sensor.plug_power", "0.0")
    await hass.async_block_till_done()
    assert hass.states.get(power_switch).state == STATE_OFF
    assert hass.states.get(entity_id(hass, "sensor", "power")).state == "0.0"

    # Commands go to the plug, never to the dryer. The entity is driven
    # directly: mocking `switch.turn_on` would also swallow the call to it.
    entity = next(
        platform.entities[power_switch]
        for platform in entity_platform.async_get_platforms(hass, DOMAIN)
        if platform.domain == "switch"
    )
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    await entity.async_turn_on()
    await entity.async_turn_off()
    assert [c.data["entity_id"] for c in turn_on] == ["switch.plug"]
    assert [c.data["entity_id"] for c in turn_off] == ["switch.plug"]
    assert not [c for c in mock_device.mock_calls if c[1].path == "/date.html"]


async def test_no_switch_without_a_configured_plug(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    await _setup(hass, config_entry)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("switch", DOMAIN, f"{DEVICE_ID}_power") is None
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_ID}_power") is None
