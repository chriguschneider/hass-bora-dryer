"""Adding a BORA: probe /info.html, errors, one entry per device id."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.bora_dryer.const import DOMAIN

from .conftest import (
    DEVICE_ID,
    HOST,
    MODEL,
    load_fixture,
    register_device,
    register_offline,
)


async def _start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_device: AiohttpClientMocker
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: f" {HOST} ", CONF_NAME: "Basement"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Basement {MODEL}"
    assert result["data"] == {CONF_HOST: HOST, CONF_NAME: "Basement"}
    assert result["result"].unique_id == DEVICE_ID


async def test_blank_name_falls_back_to_default(
    hass: HomeAssistant, mock_device: AiohttpClientMocker
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_NAME: "  "}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NAME] == "BORA"
    assert result["title"] == f"BORA {MODEL}"


async def test_same_device_id_updates_host_and_aborts(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """DHCP gave the BORA a new address: fix the entry, don't add a second one."""
    register_device(aioclient_mock, "192.0.2.99")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.99"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.0.2.99"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_cannot_connect_shows_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    register_offline(aioclient_mock)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # Once the device is on, the same form goes through.
    aioclient_mock.clear_requests()
    register_device(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_http_error_counts_as_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"http://{HOST}/info.html", status=404)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_other_device_shows_not_a_bora(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    # Any web server that answers /info.html without the BORA title.
    aioclient_mock.get(
        f"http://{HOST}/info.html", text="<html><body>router</body></html>"
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_a_bora"}


async def test_second_device_is_allowed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    register_device(aioclient_mock)
    second_info = load_fixture("info.html").replace(DEVICE_ID, "e5f6a7b8")
    register_device(aioclient_mock, "192.0.2.11", info=second_info)

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.11"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "e5f6a7b8"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def test_device_id_is_lowercased(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    register_device(
        aioclient_mock, info=load_fixture("info.html").replace(DEVICE_ID, "0A1B2C3D")
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    await hass.async_block_till_done()
    assert result["result"].unique_id == DEVICE_ID


async def test_missing_device_id_falls_back_to_host(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Existing behaviour: without a parsable id the host is the unique id."""
    info = load_fixture("info.html").replace(f"{DEVICE_ID}<br>", "")
    register_device(aioclient_mock, info=info)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == HOST
