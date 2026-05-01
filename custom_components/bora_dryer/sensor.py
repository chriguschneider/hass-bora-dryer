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
from homeassistant.const import (
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_ENERGY_SENSOR,
    CONF_POWER_SENSOR,
    DOMAIN,
    FILTER_LIFETIME_HOURS,
)
from .coordinator import BoraDataUpdateCoordinator
from .entity import BoraEntity


_UNSET: Any = object()


@dataclass(frozen=True, kw_only=True)
class BoraSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any]
    # When True, the entity stays available while the device is unreachable
    # (filter wear, firmware version, last-known operation).
    survives_offline: bool = False
    # When set (and survives_offline=True), this synthetic value is reported
    # while the device is unreachable instead of the last live value. Use for
    # state-like fields where a frozen reading would lie about reality
    # (operation: "Off" is more honest than a stuck "Drying").
    offline_value: Any = _UNSET


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
        survives_offline=True,
        offline_value="Off",
    ),
    BoraSensorEntityDescription(
        key="filter_hours",
        translation_key="filter_hours",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:air-filter",
        value_fn=lambda d: d.get("filter_hours"),
        survives_offline=True,
    ),
    BoraSensorEntityDescription(
        key="filter_remaining_hours",
        translation_key="filter_remaining_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:timer-sand",
        value_fn=_filter_remaining,
        survives_offline=True,
    ),
    BoraSensorEntityDescription(
        key="filter_progress_percent",
        translation_key="filter_progress_percent",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gauge",
        value_fn=_filter_progress_percent,
        survives_offline=True,
    ),
    BoraSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value_fn=lambda d: d.get("firmware_version"),
        survives_offline=True,
    ),
)


@dataclass(frozen=True, kw_only=True)
class BoraMirrorSensorDescription(SensorEntityDescription):
    """Describes a sensor that mirrors an upstream entity (e.g. a Shelly)."""

    options_key: str


MIRROR_SENSORS: tuple[BoraMirrorSensorDescription, ...] = (
    BoraMirrorSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        options_key=CONF_POWER_SENSOR,
    ),
    BoraMirrorSensorDescription(
        key="energy",
        translation_key="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        options_key=CONF_ENERGY_SENSOR,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a BORA config entry."""
    coordinator: BoraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [BoraSensor(coordinator, desc) for desc in SENSORS]
    for desc in MIRROR_SENSORS:
        source = entry.options.get(desc.options_key)
        if source:
            entities.append(BoraMirrorSensor(coordinator, desc, source))
    async_add_entities(entities)


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
        desc = self.entity_description
        if (
            desc.survives_offline
            and desc.offline_value is not _UNSET
            and not self.coordinator.last_update_success
        ):
            return desc.offline_value
        return desc.value_fn(self.coordinator.data or {})

    @property
    def available(self) -> bool:
        desc = self.entity_description
        if not desc.survives_offline:
            return super().available
        if desc.offline_value is not _UNSET:
            return True
        data = self.coordinator.data
        return data is not None and desc.value_fn(data) is not None


class BoraMirrorSensor(BoraEntity, SensorEntity):
    """Mirrors an upstream sensor (Shelly power/energy) under the BORA device."""

    entity_description: BoraMirrorSensorDescription

    def __init__(
        self,
        coordinator: BoraDataUpdateCoordinator,
        description: BoraMirrorSensorDescription,
        source_entity_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._source = source_entity_id
        unique_root = coordinator.entry.unique_id or coordinator.entry.data["host"]
        self._attr_unique_id = f"{unique_root}_{description.key}"

    @property
    def native_value(self) -> float | None:
        state = self.hass.states.get(self._source)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @property
    def available(self) -> bool:
        state = self.hass.states.get(self._source)
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _state_changed(event: Event[EventStateChangedData]) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source], _state_changed
            )
        )
