"""Base entity for the BORA dryer integration."""
from __future__ import annotations

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_POWER_SWITCH, DOMAIN
from .coordinator import BoraDataUpdateCoordinator


class BoraEntity(CoordinatorEntity[BoraDataUpdateCoordinator]):
    """Shared device-info wiring for all BORA entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BoraDataUpdateCoordinator) -> None:
        super().__init__(coordinator)

        data = coordinator.data or {}
        host = coordinator.entry.data["host"]
        device_id = coordinator.entry.unique_id or data.get("device_id") or host
        model = data.get("model")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer="roth-kippe ag",
            model=f"BORA {model}" if model else "BORA",
            name=coordinator.entry.data.get("name", "BORA"),
            sw_version=data.get("firmware_version"),
            serial_number=data.get("device_id"),
            configuration_url=f"http://{host}/",
            via_device=_resolve_via_device(coordinator),
        )


def _resolve_via_device(
    coordinator: BoraDataUpdateCoordinator,
) -> tuple[str, str] | None:
    """Map the configured upstream power-switch entity to its device identifier.

    Lets HA show the BORA as connected through the upstream device (e.g. a
    Shelly), so both appear linked in the device hierarchy without merging
    entities.
    """
    power_switch = coordinator.entry.options.get(CONF_POWER_SWITCH)
    if not power_switch:
        return None

    ent_entry = er.async_get(coordinator.hass).async_get(power_switch)
    if not ent_entry or not ent_entry.device_id:
        return None

    dev_entry = dr.async_get(coordinator.hass).async_get(ent_entry.device_id)
    if not dev_entry or not dev_entry.identifiers:
        return None

    return next(iter(dev_entry.identifiers))
