"""Select platform for NoLongerEvil Nest."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NLE_FAN_AUTO, NLE_FAN_ON
from .coordinator import NLECoordinator
from .entity import NLEBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NLECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(NLEFanModeSelect(coordinator, dev_id) for dev_id in coordinator.data)


class NLEFanModeSelect(NLEBaseEntity, SelectEntity):
    _attr_name = "Fan Mode"
    _attr_options = [NLE_FAN_AUTO, NLE_FAN_ON]
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_fan_mode"

    @property
    def current_option(self) -> str | None:
        return self._status.get("fan_mode", NLE_FAN_AUTO)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_fan(self._device_id, mode=option)
        await self.coordinator.async_command_refresh()
