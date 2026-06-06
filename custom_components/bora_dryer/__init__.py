"""The BORA dryer integration."""
from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import (
    FILTER_ISSUE_ID,
    FILTER_NOTIFICATION_ID,
    BoraDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BORA dryer from a config entry."""
    coordinator = BoraDataUpdateCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.warning(
            "BORA at %s not reachable at startup; entities will be "
            "unavailable until the first successful poll",
            entry.data["host"],
        )

    # Filter maintenance moved from a repair issue to a persistent notification.
    # Clear any leftover repair issue from versions <= 0.6.0 on upgrade.
    ir.async_delete_issue(hass, DOMAIN, f"{FILTER_ISSUE_ID}_{entry.entry_id}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        persistent_notification.async_dismiss(
            hass, f"{FILTER_NOTIFICATION_ID}_{entry.entry_id}"
        )
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so option changes take effect (switch entity, filter threshold)."""
    await hass.config_entries.async_reload(entry.entry_id)
