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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_FILTER_DUE_HOURS, DEFAULT_FILTER_DUE_HOURS, DOMAIN
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity


@dataclass(frozen=True, kw_only=True)
class BoraBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[BoraDataUpdateCoordinator], bool | None]
    # See sensor.BoraSensorEntityDescription.survives_offline.
    survives_offline: bool = False


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


class BoraBinarySensor(BoraEntity, BinarySensorEntity):
    """Binary sensor entity backed by the coordinator data dict."""

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

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        if not self.entity_description.survives_offline:
            return super().available
        if self.coordinator.data is None:
            return False
        return self.entity_description.value_fn(self.coordinator) is not None
