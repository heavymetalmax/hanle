"""Base entity for NoLongerEvil integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    STATUS_ID,
    STATUS_LABEL,
    STATUS_ONLINE,
    STATUS_SERIAL,
)
from .coordinator import NLECoordinator


def _find_device_meta(coordinator: NLECoordinator, device_id: str) -> dict:
    """Find static device metadata from coordinator.devices list."""
    for dev in coordinator.devices:
        did = dev.get("id") or dev.get("serial") or dev.get("deviceId")
        if did == device_id:
            return dev
    return {}


class NLEBaseEntity(CoordinatorEntity[NLECoordinator]):
    """Base class for NLE entities tied to a single device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        meta = _find_device_meta(coordinator, device_id)
        serial = meta.get(STATUS_SERIAL) or device_id

        # Best name priority:
        # 1. shared.name (user-set name on thermostat, e.g. "Ольга")
        # 2. device metadata label/name
        # 3. serial number
        status = coordinator.data.get(device_id, {}) if coordinator.data else {}
        label = (
            status.get("device_name")
            or meta.get(STATUS_LABEL)
            or meta.get("name")
            or serial
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=label,
            manufacturer="Google / Nest (NoLongerEvil)",
            model="Nest Learning Thermostat Gen 2",
            serial_number=serial,
        )

    @property
    def _status(self) -> dict:
        """Return current status dict for this device (empty if unavailable)."""
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.get(self._device_id, {})

    @property
    def available(self) -> bool:
        """Return True if coordinator has data and device reports online."""
        if not self.coordinator.last_update_success:
            return False
        status = self._status
        if not status:
            return False
        return status.get(STATUS_ONLINE, True)
