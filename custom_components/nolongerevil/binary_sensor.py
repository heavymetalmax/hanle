"""Binary sensor platform for NoLongerEvil Nest."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NLECoordinator
from .entity import NLEBaseEntity


@dataclass(frozen=True, kw_only=True)
class NLEBinarySensorDescription(BinarySensorEntityDescription):
    status_key: str
    true_values: tuple = (True, 1)
    # If set, entity is only created when this capability is True
    required_cap: str | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[NLEBinarySensorDescription, ...] = (

    NLEBinarySensorDescription(
        key="away",
        name="Away",
        device_class=BinarySensorDeviceClass.PRESENCE,
        status_key="away",
        true_values=(False, 0),  # present when NOT away
        required_cap=None,
    ),
    NLEBinarySensorDescription(
        key="fan_running",
        name="Fan Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        status_key="fan_running",
        true_values=(True, 1),
        required_cap="has_fan",
    ),
    NLEBinarySensorDescription(
        key="temperature_lock",
        name="Temperature Lock",
        device_class=None,
        status_key="temperature_lock",
        true_values=(True, 1),
        required_cap="has_lock",
    ),
    NLEBinarySensorDescription(
        key="eco_active",
        name="Eco Mode",
        device_class=None,
        status_key="eco_active",
        true_values=(True, 1),
        required_cap="has_eco",
    ),
    NLEBinarySensorDescription(
        key="leaf",
        name="Leaf (Energy Saving)",
        device_class=None,
        status_key="leaf",
        true_values=(True, 1),
        required_cap="has_leaf",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NLECoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for dev_id in coordinator.data:
        caps = coordinator.data[dev_id].get("capabilities", {})
        for desc in BINARY_SENSOR_DESCRIPTIONS:
            # Skip if this sensor requires a capability the device doesn't have
            if desc.required_cap and not caps.get(desc.required_cap):
                continue
            entities.append(NLEBinarySensor(coordinator, dev_id, desc))
    async_add_entities(entities)


class NLEBinarySensor(NLEBaseEntity, BinarySensorEntity):
    entity_description: NLEBinarySensorDescription

    def __init__(self, coordinator: NLECoordinator, device_id: str, description: NLEBinarySensorDescription) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        val = self._status.get(self.entity_description.status_key)
        if val is None:
            return None
        return val in self.entity_description.true_values
