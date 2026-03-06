"""Climate platform for NoLongerEvil — capabilities-driven, supports all Nest thermostat types."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    NLE_FAN_AUTO,
    NLE_FAN_ON,
    NLE_MODE_COOL,
    NLE_MODE_HEAT,
    NLE_MODE_OFF,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
)
from .coordinator import NLECoordinator
from .entity import NLEBaseEntity

_LOGGER = logging.getLogger(__name__)

_NLE_TO_HA_MODE = {
    "heat":  HVACMode.HEAT,
    "cool":  HVACMode.COOL,
    "auto":  HVACMode.HEAT_COOL,
    "off":   HVACMode.OFF,
}
_HA_TO_NLE_MODE = {v: k for k, v in _NLE_TO_HA_MODE.items()}

_NLE_TO_HA_ACTION = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "idle":    HVACAction.IDLE,
    "off":     HVACAction.OFF,
}

_FAN_MODES = [NLE_FAN_AUTO, NLE_FAN_ON]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NLECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(NLEClimate(coordinator, dev_id) for dev_id in coordinator.data)


class NLEClimate(NLEBaseEntity, ClimateEntity):
    """Thermostat entity for NoLongerEvil.

    Features are determined at runtime from the capabilities dict returned by
    parse_status(), so Heat Links, heat-only thermostats, and full heat/cool
    units all work correctly without any per-model branching.
    """

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 9.0
    _attr_max_temp = 32.0
    _attr_preset_modes = [PRESET_HOME, PRESET_AWAY, PRESET_ECO]

    def __init__(self, coordinator: NLECoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_climate"

    # ── Capability helpers ────────────────────────────────────────────────────

    @property
    def _caps(self) -> dict:
        return self._status.get("capabilities", {})

    # ── Dynamic features & modes (override _attr_* with @property) ───────────

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes: list[HVACMode] = [HVACMode.HEAT, HVACMode.OFF]
        if self._caps.get("can_cool"):
            modes.insert(1, HVACMode.COOL)
            modes.insert(2, HVACMode.HEAT_COOL)
        return modes

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if self._caps.get("can_cool"):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if self._caps.get("has_fan"):
            features |= ClimateEntityFeature.FAN_MODE
        return features

    @property
    def fan_modes(self) -> list[str] | None:
        return _FAN_MODES if self._caps.get("has_fan") else None

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def current_temperature(self) -> float | None:
        return self._status.get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        # Only meaningful in single-target modes (heat / cool)
        if self._caps.get("has_range") and self._status.get("hvac_mode") == "auto":
            return None
        return self._status.get("target_temperature")

    @property
    def target_temperature_high(self) -> float | None:
        return self._status.get("target_temperature_high")

    @property
    def target_temperature_low(self) -> float | None:
        return self._status.get("target_temperature_low")

    @property
    def current_humidity(self) -> int | None:
        if not self._caps.get("has_humidity"):
            return None
        h = self._status.get("humidity")
        return int(h) if h is not None else None

    @property
    def hvac_mode(self) -> HVACMode:
        return _NLE_TO_HA_MODE.get(self._status.get("hvac_mode", "off"), HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction | None:
        return _NLE_TO_HA_ACTION.get(self._status.get("hvac_action", ""))

    @property
    def fan_mode(self) -> str | None:
        if not self._caps.get("has_fan"):
            return None
        return self._status.get("fan_mode", NLE_FAN_AUTO)

    @property
    def preset_mode(self) -> str:
        if self._caps.get("has_eco") and self._status.get("eco_active"):
            return PRESET_ECO
        if self._status.get("away"):
            return PRESET_AWAY
        return PRESET_HOME

    # ── Commands ──────────────────────────────────────────────────────────────

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        nle_mode = _HA_TO_NLE_MODE.get(hvac_mode, NLE_MODE_OFF)
        await self.coordinator.client.set_mode(self._device_id, nle_mode)
        await self.coordinator.async_command_refresh()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        temp_high = kwargs.get("target_temp_high")
        temp_low = kwargs.get("target_temp_low")

        if temp_high is not None and temp_low is not None:
            # Heat/cool range mode
            await self.coordinator.client.set_temperature_range(
                self._device_id, heat=temp_low, cool=temp_high
            )
        elif temp is not None:
            # Single target — use current hvac_mode to pick heat or cool
            nle_mode = _HA_TO_NLE_MODE.get(self.hvac_mode, NLE_MODE_HEAT)
            await self.coordinator.client.set_temperature(
                self._device_id, value=temp, mode=nle_mode
            )
        await self.coordinator.async_command_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if not self._caps.get("has_fan"):
            return
        await self.coordinator.client.set_fan(self._device_id, mode=fan_mode)
        await self.coordinator.async_command_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_AWAY:
            await self.coordinator.client.set_away(self._device_id, away=True)
        elif preset_mode == PRESET_ECO and self._caps.get("has_eco"):
            await self.coordinator.client.set_mode(self._device_id, "eco")
        else:  # PRESET_HOME
            await self.coordinator.client.set_away(self._device_id, away=False)
        await self.coordinator.async_command_refresh()
