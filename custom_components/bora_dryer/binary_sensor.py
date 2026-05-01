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

from .const import DOMAIN, FILTER_DUE_HOURS
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity


@dataclass(frozen=True, kw_only=True)
class BoraBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _is_drying(data: dict[str, Any]) -> bool | None:
    op = data.get("operation_state")
    if op is None:
        return None
    return "Drying" in op


def _filter_due(data: dict[str, Any]) -> bool | None:
    hours = data.get("filter_hours")
    if hours is None:
        return None
    return hours >= FILTER_DUE_HOURS


BINARY_SENSORS: tuple[BoraBinarySensorEntityDescription, ...] = (
    BoraBinarySensorEntityDescription(
        key="is_drying",
        translation_key="is_drying",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=_is_drying,
    ),
    BoraBinarySensorEntityDescription(
        key="filter_due",
        translation_key="filter_due",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_filter_due,
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
        return self.entity_description.value_fn(self.coordinator.data or {})
