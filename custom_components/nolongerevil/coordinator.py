"""DataUpdateCoordinator for NoLongerEvil — parses real NLE API response."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NLEApiClient, NLEAuthError, NLEConnectionError, NLERateLimitError
from .const import (
    BATTERY_EMPTY_V,
    BATTERY_FULL_V,
    DEV_AWAY_TEMP_HIGH,
    DEV_AWAY_TEMP_LOW,
    DEV_BACKPLATE_TEMP,
    DEV_BATTERY,
    DEV_ECO,
    DEV_FAN_MODE,
    DEV_FAN_SPEED,
    DEV_HAS_FAN,
    DEV_HEAT_LINK_MODEL,
    DEV_HEAT_LINK_SW,
    DEV_HOT_WATER,
    DEV_HUMIDITY,
    DEV_LEAF,
    DEV_LOCK_HIGH,
    DEV_LOCK_LOW,
    DEV_LOCKED,
    DEV_RSSI,
    DEV_SCHEDULE_MODE,
    DEV_SWITCH_OFF,
    DOMAIN,
    SHARED_CAN_COOL,
    SHARED_CAN_HEAT,
    SHARED_CURRENT_TEMP,
    SHARED_HVAC_AC_STATE,
    SHARED_HVAC_HEATER_STATE,
    SHARED_TARGET_TEMP,
    SHARED_TARGET_TEMP_TYPE,
    SHARED_TARGET_TEMP_HIGH,
    SHARED_TARGET_TEMP_LOW,
    STRUCT_AWAY,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)


def _battery_volts_to_pct(volts: float | None) -> int | None:
    if volts is None:
        return None
    pct = (volts - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V) * 100
    return max(0, min(100, round(pct)))


def parse_status(raw: dict) -> dict[str, Any]:
    """Flatten nested NLE status response into a simple key->value dict."""
    state: dict = raw.get("state", {})
    device_meta: dict = raw.get("device", {})
    # API keys use serial number, not UUID — must read serial from device metadata
    serial: str = device_meta.get("serial", "")

    shared_val: dict = {}
    device_val: dict = {}
    struct_val: dict = {}
    schedule_val: dict = {}

    for key, obj in state.items():
        val = obj.get("value", {})
        # Match by serial (not UUID) — serial may also be inside value as serial_number
        if not serial:
            # Fallback: try to extract serial from device value if metadata missing
            if key.startswith("device."):
                _maybe_serial = obj.get("value", {}).get("serial_number", "")
                if _maybe_serial:
                    serial = _maybe_serial
        if key == f"shared.{serial}":
            shared_val = val
        elif key == f"device.{serial}":
            device_val = val
        elif key.startswith("structure."):
            struct_val = val
        elif key == f"schedule.{serial}":
            schedule_val = val

    # HVAC mode: target_temperature_type in shared is the most reliable source.
    # Values: "heat" | "cool" | "range" | "off"
    # Falls back to current_schedule_mode from device if absent.
    _mode_map = {"heat": "heat", "cool": "cool", "auto": "auto", "off": "off",
                 "HEAT": "heat", "COOL": "cool", "AUTO": "auto", "OFF": "off"}
    sched_mode_raw: str = device_val.get(DEV_SCHEDULE_MODE, "HEAT")
    target_temp_type: str = shared_val.get(SHARED_TARGET_TEMP_TYPE, "").lower()
    if target_temp_type:
        hvac_mode = _mode_map.get(target_temp_type, "heat")
    else:
        # fallback for devices that don't have target_temperature_type
        system_off: bool = bool(device_val.get(DEV_SWITCH_OFF, False))
        if system_off:
            hvac_mode = "off"
        else:
            hvac_mode = _mode_map.get(sched_mode_raw.upper(), "heat")

    # HVAC action: use real hvac_*_state fields from shared object (most reliable).
    # Heat Link uses hot_water_boiling_state as fallback.
    heater_state: bool = bool(shared_val.get(SHARED_HVAC_HEATER_STATE, False))
    ac_state: bool = bool(shared_val.get(SHARED_HVAC_AC_STATE, False))
    boiling_raw = device_val.get(DEV_HOT_WATER)

    if hvac_mode == "off":
        hvac_action = "off"
    elif heater_state:
        hvac_action = "heating"
    elif ac_state:
        hvac_action = "cooling"
    else:
        hvac_action = "idle" 

    # eco_mode_enabled is a plain boolean in the real API response
    eco_active: bool = bool(device_val.get(DEV_ECO, False))

    away: bool = bool(struct_val.get(STRUCT_AWAY, False))

    battery_v: float | None = device_val.get(DEV_BATTERY)
    battery_pct: int | None = _battery_volts_to_pct(battery_v)

    fan_speed: str = device_val.get(DEV_FAN_SPEED, "off")
    fan_running: bool = fan_speed not in ("off", "none", "")

    # ── Capability detection ──────────────────────────────────────────────────
    # can_heat / can_cool come directly from shared object — most reliable source.
    # has_fan uses the explicit has_fan field from device object (Nest provides it).
    can_heat: bool = bool(shared_val.get(SHARED_CAN_HEAT, True))
    can_cool: bool = bool(shared_val.get(SHARED_CAN_COOL, False))

    capabilities = {
        "has_heat_link":  DEV_HEAT_LINK_MODEL in device_val,
        "has_hot_water":  DEV_HOT_WATER in device_val,
        "has_fan":        bool(device_val.get(DEV_HAS_FAN, DEV_FAN_MODE in device_val)),
        "has_fan_speed":  DEV_FAN_SPEED in device_val,
        "has_humidity":   DEV_HUMIDITY in device_val,
        "has_battery":    DEV_BATTERY in device_val,
        "can_heat":       can_heat,
        "can_cool":       can_cool,
        "has_range":      can_heat and can_cool,
        "has_eco":        DEV_ECO in device_val,          # key present = eco supported
        "has_leaf":       DEV_LEAF in device_val,
        "has_lock":       DEV_LOCKED in device_val,
        "has_away_temps": DEV_AWAY_TEMP_LOW in device_val,
    }

    return {
        "current_temperature": shared_val.get(SHARED_CURRENT_TEMP),
        "target_temperature": shared_val.get(SHARED_TARGET_TEMP),
        "target_temperature_high": shared_val.get(SHARED_TARGET_TEMP_HIGH),
        "target_temperature_low": shared_val.get(SHARED_TARGET_TEMP_LOW),
        "hvac_mode": hvac_mode,
        "hvac_action": hvac_action,
        "humidity": device_val.get(DEV_HUMIDITY),
        "fan_mode": device_val.get(DEV_FAN_MODE, "auto"),
        "fan_running": fan_running,
        "away": away,
        "eco_active": eco_active,
        "temperature_lock": bool(device_val.get(DEV_LOCKED, False)),
        "lock_temp_low": device_val.get(DEV_LOCK_LOW),
        "lock_temp_high": device_val.get(DEV_LOCK_HIGH),
        "away_temperature_low": device_val.get(DEV_AWAY_TEMP_LOW),
        "away_temperature_high": device_val.get(DEV_AWAY_TEMP_HIGH),
        "battery_level": battery_pct,
        "battery_voltage": battery_v,
        "leaf": bool(device_val.get(DEV_LEAF, False)),
        "backplate_temperature": device_val.get(DEV_BACKPLATE_TEMP),
        "heat_link_model": device_val.get(DEV_HEAT_LINK_MODEL),
        "heat_link_sw": device_val.get(DEV_HEAT_LINK_SW),
        "rssi": device_val.get(DEV_RSSI),
        "schedule": schedule_val,
        "capabilities": capabilities,
        "device_name": shared_val.get("name") or device_meta.get("name") or "",
        "_device_meta": device_meta,
    }


class NLECoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache status for all NLE devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NLEApiClient,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )
        self.client = client
        self.devices: list[dict] = []
        self._command_pending: bool = False

    async def async_command_refresh(self) -> None:
        """Request refresh after a command, with a short delay to let the
        device apply the change and avoid immediate rate-limit hits."""
        import asyncio
        if self._command_pending:
            return  # already waiting, skip duplicate
        self._command_pending = True
        await asyncio.sleep(3)  # give device 3s to apply the change
        self._command_pending = False
        await self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if not self.devices:
                self.devices = await self.client.list_devices()
                _LOGGER.debug("Discovered %d NLE device(s)", len(self.devices))
                if not self.devices:
                    _LOGGER.warning(
                        "NLE API returned an empty device list. "
                        "Check your API key permissions or that devices exist in your account."
                    )

            statuses: dict[str, Any] = {}
            for device in self.devices:
                dev_id = device.get("id") or device.get("serial") or device.get("deviceId")
                if not dev_id:
                    _LOGGER.warning("Device without ID: %s", device)
                    continue
                raw = await self.client.get_status(dev_id)
                statuses[dev_id] = parse_status(raw)
                _LOGGER.debug("Parsed status for %s: %s", dev_id, statuses[dev_id])
            return statuses

        except NLEAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except NLERateLimitError as err:
            _LOGGER.warning("NLE rate limit hit, will retry: %s", err)
            return self.data or {}
        except NLEConnectionError as err:
            raise UpdateFailed(f"Cannot reach NLE API: {err}") from err
