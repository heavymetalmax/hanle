"""Number platform for NoLongerEvil Nest — temperature lock range."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NLECoordinator
from .entity import NLEBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NLECoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for dev_id in coordinator.data:
        # Only create lock temp entities for devices that support temperature lock
        if coordinator.data[dev_id].get("capabilities", {}).get("has_lock"):
            entities.append(NLELockTempMin(coordinator, dev_id))
            entities.append(NLELockTempMax(coordinator, dev_id))
    async_add_entities(entities)


class _NLELockTempBase(NLEBaseEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 9.0
    _attr_native_max_value = 32.0
    _attr_native_step = 0.5

    def __init__(self, coordinator: NLECoordinator, device_id: str, key: str, name: str) -> None:
        super().__init__(coordinator, device_id)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def native_value(self) -> float | None:
        return self._status.get(self._key)

    @property
    def available(self) -> bool:
        # Only available when lock is actually enabled
        return super().available and bool(self._status.get("temperature_lock", False))


class NLELockTempMin(_NLELockTempBase):
    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "lock_temp_low", "Lock Minimum Temperature")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_lock(
            self._device_id, enabled=True, min_temp=value,
            max_temp=self._status.get("lock_temp_high"),
        )
        await self.coordinator.async_command_refresh()


class NLELockTempMax(_NLELockTempBase):
    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "lock_temp_high", "Lock Maximum Temperature")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_lock(
            self._device_id, enabled=True, min_temp=self._status.get("lock_temp_low"),
            max_temp=value,
        )
        await self.coordinator.async_command_refresh()
