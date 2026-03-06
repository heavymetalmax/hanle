"""Sensor platform for NoLongerEvil Nest."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NLECoordinator
from .entity import NLEBaseEntity


@dataclass(frozen=True, kw_only=True)
class NLESensorDescription(SensorEntityDescription):
    status_key: str


SENSOR_DESCRIPTIONS: tuple[NLESensorDescription, ...] = (
    NLESensorDescription(
        key="current_temperature",
        name="Current Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        status_key="current_temperature",
    ),
    NLESensorDescription(
        key="target_temperature",
        name="Target Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        status_key="target_temperature",
    ),
    NLESensorDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        status_key="humidity",
    ),
    NLESensorDescription(
        key="battery_level",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        status_key="battery_level",
    ),
    NLESensorDescription(
        key="backplate_temperature",
        name="Backplate Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
        status_key="backplate_temperature",
    ),
    NLESensorDescription(
        key="rssi",
        name="Wi-Fi Signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
        status_key="rssi",
    ),
    NLESensorDescription(
        key="away_temperature_low",
        name="Away Temperature (Low)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
        status_key="away_temperature_low",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NLECoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        NLESensor(coordinator, dev_id, desc)
        for dev_id in coordinator.data
        for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class NLESensor(NLEBaseEntity, SensorEntity):
    entity_description: NLESensorDescription

    def __init__(self, coordinator: NLECoordinator, device_id: str, description: NLESensorDescription) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self._status.get(self.entity_description.status_key)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None
