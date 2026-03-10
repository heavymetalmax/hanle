"""Switch platform for NoLongerEvil Nest."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities(NLEAwaySwitch(coordinator, dev_id) for dev_id in coordinator.data)


class NLEAwaySwitch(NLEBaseEntity, SwitchEntity):
    """Toggle away mode."""
    _attr_name = "Away Mode"
    _attr_icon = "mdi:home-export-outline"

    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_away_switch"

    @property
    def is_on(self) -> bool:
        return bool(self._status.get("away", False))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.set_away(self._device_id, away=True)
        await self.coordinator.async_command_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.set_away(self._device_id, away=False)
        await self.coordinator.async_command_refresh()
