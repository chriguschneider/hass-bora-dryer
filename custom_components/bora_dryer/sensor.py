"""Sensor platform for the BORA dryer."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FILTER_LIFETIME_HOURS
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity


@dataclass(frozen=True, kw_only=True)
class BoraSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _filter_remaining(data: dict[str, Any]) -> int | None:
    hours = data.get("filter_hours")
    if hours is None:
        return None
    return max(FILTER_LIFETIME_HOURS - hours, 0)


def _filter_progress_percent(data: dict[str, Any]) -> int | None:
    hours = data.get("filter_hours")
    if hours is None:
        return None
    pct = round(hours / FILTER_LIFETIME_HOURS * 100)
    return max(0, min(100, pct))


SENSORS: tuple[BoraSensorEntityDescription, ...] = (
    BoraSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("temperature"),
    ),
    BoraSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("humidity"),
    ),
    BoraSensorEntityDescription(
        key="operation_state",
        translation_key="operation_state",
        icon="mdi:state-machine",
        value_fn=lambda d: d.get("operation_state"),
    ),
    BoraSensorEntityDescription(
        key="filter_hours",
        translation_key="filter_hours",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:air-filter",
        value_fn=lambda d: d.get("filter_hours"),
    ),
    BoraSensorEntityDescription(
        key="filter_remaining_hours",
        translation_key="filter_remaining_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:timer-sand",
        value_fn=_filter_remaining,
    ),
    BoraSensorEntityDescription(
        key="filter_progress_percent",
        translation_key="filter_progress_percent",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
        value_fn=_filter_progress_percent,
    ),
    BoraSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value_fn=lambda d: d.get("firmware_version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a BORA config entry."""
    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(BoraSensor(coordinator, desc) for desc in SENSORS)


class BoraSensor(BoraEntity, SensorEntity):
    """Sensor entity backed by the coordinator data dict."""

    entity_description: BoraSensorEntityDescription

    def __init__(
        self,
        coordinator: BoraDataUpdateCoordinator,
        description: BoraSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
