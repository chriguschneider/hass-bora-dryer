"""Binary sensor platform for the BORA dryer."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_FILTER_DUE_HOURS, DEFAULT_FILTER_DUE_HOURS, DOMAIN
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity


_UNSET: Any = object()


@dataclass(frozen=True, kw_only=True)
class BoraBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[BoraDataUpdateCoordinator], bool | None]
    # See sensor.BoraSensorEntityDescription.survives_offline / offline_value.
    survives_offline: bool = False
    offline_value: Any = _UNSET


def _is_drying(coordinator: BoraDataUpdateCoordinator) -> bool | None:
    op = (coordinator.data or {}).get("operation_state")
    if op is None:
        return None
    return "Drying" in op


def _filter_due(coordinator: BoraDataUpdateCoordinator) -> bool | None:
    hours = (coordinator.data or {}).get("filter_hours")
    if hours is None:
        return None
    threshold = coordinator.entry.options.get(
        CONF_FILTER_DUE_HOURS, DEFAULT_FILTER_DUE_HOURS
    )
    return hours >= threshold


BINARY_SENSORS: tuple[BoraBinarySensorEntityDescription, ...] = (
    BoraBinarySensorEntityDescription(
        key="is_drying",
        translation_key="is_drying",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=_is_drying,
        survives_offline=True,
        offline_value=False,
    ),
    BoraBinarySensorEntityDescription(
        key="filter_due",
        translation_key="filter_due",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_filter_due,
        survives_offline=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for a BORA config entry."""
    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BoraBinarySensor(coordinator, desc) for desc in BINARY_SENSORS)


class BoraBinarySensor(BoraEntity, RestoreEntity, BinarySensorEntity):
    """Binary sensor entity backed by the coordinator data dict.

    `survives_offline` descriptions keep their last state while the device is
    unreachable and restore it across a Home Assistant restart, so they never
    fall back to "unavailable" once they have reported at least once.
    """

    entity_description: BoraBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BoraDataUpdateCoordinator,
        description: BoraBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_{description.key}"
        self._restored_is_on: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.entity_description.survives_offline:
            if (last := await self.async_get_last_state()) is not None:
                if last.state in (STATE_ON, STATE_OFF):
                    self._restored_is_on = last.state == STATE_ON

    @callback
    def _handle_coordinator_update(self) -> None:
        # Remember the newest good state so it can be held while the device is
        # offline, even if HA is not restarted in between.
        if self.entity_description.survives_offline:
            live = self.entity_description.value_fn(self.coordinator)
            if live is not None:
                self._restored_is_on = live
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool | None:
        desc = self.entity_description
        if (
            desc.survives_offline
            and desc.offline_value is not _UNSET
            and not self.coordinator.last_update_success
        ):
            return desc.offline_value
        live = desc.value_fn(self.coordinator)
        if live is not None or not desc.survives_offline:
            return live
        # Device offline / not yet polled: hold the last known state, restored
        # from the state store after a restart.
        return self._restored_is_on

    @property
    def available(self) -> bool:
        desc = self.entity_description
        if not desc.survives_offline:
            return super().available
        if desc.offline_value is not _UNSET:
            return True
        return desc.value_fn(self.coordinator) is not None or self._restored_is_on is not None
