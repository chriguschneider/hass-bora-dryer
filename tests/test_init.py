"""Entry setup, unload, the upgrade clean-up and the options flow."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bora_dryer.const import (
    CONF_FILTER_DUE_HOURS,
    CONF_FILTER_NOTIFY,
    CONF_POWER_SWITCH,
    DOMAIN,
)
from custom_components.bora_dryer.coordinator import (
    FILTER_ISSUE_ID,
    FILTER_NOTIFICATION_ID,
    BoraDataUpdateCoordinator,
)


async def test_setup_and_unload(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert isinstance(coordinator, BoraDataUpdateCoordinator)

    notification_id = f"{FILTER_NOTIFICATION_ID}_{config_entry.entry_id}"
    persistent_notification.async_create(hass, "due", notification_id=notification_id)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]
    # Unloading takes the filter reminder with it.
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert notification_id not in notifications


async def test_setup_removes_the_legacy_repair_issue(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    """v0.4.0-v0.6.0 raised a repair issue; v0.7.0+ removes it on upgrade."""
    issue_id = f"{FILTER_ISSUE_ID}_{config_entry.entry_id}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="filter_maintenance_due",
    )
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_options_are_stored_and_reload_the_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_device
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    before = hass.data[DOMAIN][config_entry.entry_id]

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_FILTER_DUE_HOURS: 250, CONF_FILTER_NOTIFY: False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    # Unset entity selectors are not stored at all.
    assert config_entry.options == {
        CONF_FILTER_DUE_HOURS: 250,
        CONF_FILTER_NOTIFY: False,
    }
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.data[DOMAIN][config_entry.entry_id] is not before


async def test_options_drop_a_cleared_entity_selector(
    hass: HomeAssistant, mock_device
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="0a1b2c3d",
        data={"host": "192.0.2.10"},
        options={CONF_POWER_SWITCH: "switch.plug"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        # A cleared selector is simply absent from the submitted form.
        {CONF_FILTER_DUE_HOURS: 280, CONF_FILTER_NOTIFY: True},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_POWER_SWITCH not in entry.options
