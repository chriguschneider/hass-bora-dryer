"""Sensor platform for the BORA dryer."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
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
    CONF_HUMIDITY_SENSOR,
    CONF_POWER_SENSOR,
    CONF_TEMPERATURE_SENSOR,
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
    # When True, the entity keeps its last known value while the device is
    # unreachable instead of going unavailable, and that value is restored from
    # HA's state store on restart — so a cold start with the device off still
    # shows the last reading rather than "unavailable" (filter wear, firmware
    # version, last temperature/humidity, last-known operation).
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
        survives_offline=True,
    ),
    BoraSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("humidity"),
        survives_offline=True,
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


# Sensors that can fall back to an external entity when the BORA reading is
# unavailable (device offline or value missing). Keyed by the sensor description
# `key` so we look up the matching options entry at setup time.
FALLBACK_SOURCES: dict[str, str] = {
    "temperature": CONF_TEMPERATURE_SENSOR,
    "humidity": CONF_HUMIDITY_SENSOR,
}


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
    entities: list[SensorEntity] = []
    for desc in SENSORS:
        fallback_key = FALLBACK_SOURCES.get(desc.key)
        source = entry.options.get(fallback_key) if fallback_key else None
        if source:
            entities.append(BoraFallbackSensor(coordinator, desc, source))
        else:
            entities.append(BoraSensor(coordinator, desc))
    for desc in MIRROR_SENSORS:
        source = entry.options.get(desc.options_key)
        if source:
            entities.append(BoraMirrorSensor(coordinator, desc, source))
    async_add_entities(entities)


class BoraSensor(BoraEntity, RestoreSensor):
    """Sensor entity backed by the coordinator data dict.

    For `survives_offline` descriptions the last value is remembered across the
    device being unreachable *and* across a Home Assistant restart (restored
    from the state store in `async_added_to_hass`), so the entity never falls
    back to "unavailable" once it has reported at least once.
    """

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
        self._restored_value: Any = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.entity_description.survives_offline:
            if (last := await self.async_get_last_sensor_data()) is not None:
                self._restored_value = last.native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        # Remember the newest good reading so it can be held while the device is
        # offline, even if HA is not restarted in between.
        if self.entity_description.survives_offline:
            live = self._live_value()
            if live is not None:
                self._restored_value = live
        super()._handle_coordinator_update()

    def _live_value(self) -> Any:
        """The current reading from the coordinator, or None if not present."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def native_value(self) -> Any:
        desc = self.entity_description
        if (
            desc.survives_offline
            and desc.offline_value is not _UNSET
            and not self.coordinator.last_update_success
        ):
            return desc.offline_value
        live = self._live_value()
        if live is not None or not desc.survives_offline:
            return live
        # Device offline / not yet polled: hold the last known value, restored
        # from the state store after a restart.
        return self._restored_value

    @property
    def available(self) -> bool:
        desc = self.entity_description
        if not desc.survives_offline:
            return super().available
        if desc.offline_value is not _UNSET:
            return True
        return self._live_value() is not None or self._restored_value is not None


class BoraFallbackSensor(BoraSensor):
    """BORA sensor that uses an external entity when the device value is unavailable."""

    def __init__(
        self,
        coordinator: BoraDataUpdateCoordinator,
        description: BoraSensorEntityDescription,
        source_entity_id: str,
    ) -> None:
        super().__init__(coordinator, description)
        self._source = source_entity_id

    def _live_value(self) -> Any:
        if not self.coordinator.last_update_success:
            return None
        return self.entity_description.value_fn(self.coordinator.data or {})

    def _external_value(self) -> float | None:
        state = self.hass.states.get(self._source)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @property
    def native_value(self) -> Any:
        live = self._live_value()
        if live is not None:
            return live
        external = self._external_value()
        if external is not None:
            return external
        # No live reading and no external fallback: hold the last known value
        # (restored across restarts) rather than go unavailable.
        return self._restored_value

    @property
    def available(self) -> bool:
        return (
            self._live_value() is not None
            or self._external_value() is not None
            or self._restored_value is not None
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
