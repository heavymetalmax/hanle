# NoLongerEvil Nest — Home Assistant Integration

Custom integration for Home Assistant that controls **Nest Gen 1 / Gen 2 thermostats** running [NoLongerEvil](https://nolongerevil.com) firmware via the official NLE REST API.

## Features

| Entity | Description |
|---|---|
| `climate.*` | Full thermostat control: Heat / Cool / Heat-Cool / Off, target temperature, fan mode, Away preset |
| `sensor.current_temperature` | Current room temperature |
| `sensor.humidity` | Current relative humidity |
| `sensor.target_temperature` | Current target temperature (single setpoint) |
| `sensor.target_temperature_high/low` | Heat/cool range setpoints (auto mode) |
| `sensor.battery_level` | Battery percentage |
| `binary_sensor.online` | Device connectivity |
| `binary_sensor.heating` | Active heating indicator |
| `binary_sensor.cooling` | Active cooling indicator |
| `binary_sensor.fan_running` | Fan running indicator |
| `binary_sensor.away` | Presence / Away state |
| `binary_sensor.temperature_locked` | Temperature lock active |
| `switch.away_mode` | Toggle away mode on/off |
| `select.fan_mode` | Fan mode: `auto` / `on` |
| `number.lock_minimum/maximum_temperature` | Temperature lock range |

## Requirements

- Nest Gen 1 or Gen 2 thermostat flashed with NoLongerEvil firmware
- NoLongerEvil account with an API key (read + write scopes) from https://nolongerevil.com/settings
- Home Assistant 2024.1 or newer

## Installation (Manual)

1. Copy the `custom_components/nolongerevil` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → search "NoLongerEvil"**.
4. Enter your API key and (optionally) your self-hosted server URL.

## Installation (HACS)

1. In HACS, add this repository as a custom integration.
2. Install and restart HA.

## Configuration

| Field | Required | Default | Description |
|---|---|---|---|
| API Key | ✅ | — | NLE API key starting with `nle_` |
| Server URL | ❌ | `https://nolongerevil.com/api/v1` | Use for self-hosted NLE server |
| Poll interval | ❌ | `60` seconds | Configurable in Options (min 30s) |

> **Rate limit note:** The hosted NLE API allows 20 requests/minute per API key.  
> With 1 thermostat, each poll = 2 requests (list + status). 60s interval = 2 req/min — well within limits.

## Heat Link (Gen 2 EU)

This integration works with the **Nest Learning Thermostat Gen 2 + Heat Link** combination. The `climate` entity will only expose `heat` and `off` modes if that's what NLE reports for your device.

## Troubleshooting

- **"Cannot connect"** during setup: Verify your internet connection and that `https://nolongerevil.com/api/v1/devices` is reachable.
- **Entity unavailable**: Device may be offline. Check the NLE dashboard.
- **Status fields missing**: NLE may use slightly different JSON field names. Check HA logs (`Settings → System → Logs`) and open an issue with the raw status JSON.

## Notes

- This integration uses **polling** (not push/websocket), so there's a delay of up to `scan_interval` seconds before state changes are reflected.
- The NLE API is unofficial and subject to change. If it breaks, check the [NLE GitHub](https://github.com/codykociemba/NoLongerEvil-Thermostat) for updates.
