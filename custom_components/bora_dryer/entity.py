"""Base entity for the BORA dryer integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
        )
