"""Power switch platform for the BORA dryer.

The BORA web interface offers no remote on/off, so this entity delegates to a
user-configured underlying switch entity (typically a smart plug like a Shelly
in front of the dryer). Configure via the integration's options flow.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_POWER_SWITCH, DOMAIN
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the power switch only when an underlying entity is configured."""
    underlying = entry.options.get(CONF_POWER_SWITCH)
    if not underlying:
        _LOGGER.debug("No power switch configured for %s; skipping switch entity", entry.title)
        return

    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BoraPowerSwitch(coordinator, underlying)])


class BoraPowerSwitch(BoraEntity, SwitchEntity):
    """Mirrors and controls a configured upstream switch entity."""

    _attr_translation_key = "power"
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(
        self,
        coordinator: BoraDataUpdateCoordinator,
        underlying_entity_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._underlying = underlying_entity_id
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_power"

    @property
    def is_on(self) -> bool | None:
        state = self.hass.states.get(self._underlying)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state == STATE_ON

    @property
    def available(self) -> bool:
        state = self.hass.states.get(self._underlying)
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    async def async_added_to_hass(self) -> None:
        """Track upstream state so HA pushes updates to the wrapped switch."""
        await super().async_added_to_hass()

        @callback
        def _state_changed(event: Event[EventStateChangedData]) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._underlying], _state_changed
            )
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            Platform.SWITCH.value,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._underlying},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            Platform.SWITCH.value,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._underlying},
            blocking=True,
        )
