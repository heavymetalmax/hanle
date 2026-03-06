"""Constants for the NoLongerEvil integration."""

DOMAIN = "nolongerevil"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_BASE_URL = "https://nolongerevil.com/api/v1"
DEFAULT_SCAN_INTERVAL = 60  # seconds

# NLE API HVAC mode strings (used in API calls)
NLE_MODE_HEAT = "heat"
NLE_MODE_COOL = "cool"
NLE_MODE_AUTO = "auto"
NLE_MODE_OFF = "off"

# NLE API fan mode strings
NLE_FAN_ON = "on"
NLE_FAN_AUTO = "auto"

# ── Real NLE API response structure ──────────────────────────────────────────
# GET /thermostat/{id}/status returns:
# {
#   "device": { "id": ..., "serial": ..., "name": ... },
#   "state": {
#     "shared.{serial}":   { "value": { current_temperature, target_temperature, ... } }
#     "device.{serial}":   { "value": { current_humidity, battery_level, fan_mode, ... } }
#     "structure.{id}":    { "value": { away: false, ... } }
#     "schedule.{serial}": { "value": { days: {...}, schedule_mode: "HEAT" } }
#   }
# }

# Keys inside shared.{serial}.value
SHARED_CURRENT_TEMP = "current_temperature"         # 20.79999
SHARED_TARGET_TEMP = "target_temperature"           # 18
SHARED_TARGET_TEMP_HIGH = "target_temperature_high" # heat-cool mode only
SHARED_TARGET_TEMP_LOW = "target_temperature_low"   # heat-cool mode only
SHARED_HVAC_HEATER_STATE = "hvac_heater_state"      # true = heat relay active
SHARED_HVAC_AC_STATE = "hvac_ac_state"              # true = cool relay active
SHARED_HVAC_FAN_STATE = "hvac_fan_state"            # true = fan running
SHARED_CAN_HEAT = "can_heat"                        # device supports heating
SHARED_CAN_COOL = "can_cool"                        # device supports cooling
SHARED_TARGET_TEMP_TYPE = "target_temperature_type" # "heat" | "cool" | "range"

# Keys inside device.{serial}.value
DEV_HUMIDITY = "current_humidity"                   # 37
DEV_BATTERY = "battery_level"                       # 3.891 volts
DEV_FAN_MODE = "fan_mode"                           # "auto"
DEV_FAN_SPEED = "fan_current_speed"                 # "off" / "stage1"
DEV_SCHEDULE_MODE = "current_schedule_mode"         # "HEAT"
DEV_LOCKED = "temperature_lock"                     # false
DEV_LOCK_LOW = "temperature_lock_low_temp"          # 20
DEV_LOCK_HIGH = "temperature_lock_high_temp"        # 22.22223
DEV_HOT_WATER = "hot_water_boiling_state"           # true (Heat Link actively boiling)
DEV_AWAY_TEMP_LOW = "away_temperature_low"          # 9.4444
DEV_AWAY_TEMP_HIGH = "away_temperature_high"        # 24.44444
DEV_ECO = "eco"                                     # {"mode": "schedule"|"manual-eco"}
DEV_LEAF = "leaf"                                   # true = energy saving active
DEV_BACKPLATE_TEMP = "backplate_temperature"        # 20.79999
DEV_HEATER_DELIVERY = "heater_delivery"             # "in-floor-radiant"
DEV_HEAT_LINK_MODEL = "heat_link_model"             # "Amber-1.5"
DEV_HEAT_LINK_SW = "heat_link_sw_version"           # "2.1.2-1"
DEV_RSSI = "rssi"                                   # 69
DEV_SWITCH_OFF = "switch_system_off"                # true = system turned off
DEV_HAS_FAN = "has_fan"                             # true = fan physically wired

# Keys inside structure.{id}.value
STRUCT_AWAY = "away"                                # false

# Keys inside schedule.{serial}.value
SCHED_DAYS = "days"
SCHED_MODE = "schedule_mode"                        # "HEAT"

# Preset names
PRESET_ECO = "eco"
PRESET_HOME = "home"
PRESET_AWAY = "away"

# Heat Link Gen 2 is heat-only
HEAT_LINK_HVAC_MODES = [NLE_MODE_HEAT, NLE_MODE_OFF]

# Battery: NLE returns volts (3.891 V typical). Map to % for HA.
BATTERY_FULL_V = 4.2
BATTERY_EMPTY_V = 3.0

# Keys used in device metadata (from list_devices response)
STATUS_ID = "id"
STATUS_SERIAL = "serial"
STATUS_LABEL = "label"
STATUS_ONLINE = "online"
STATUS_BATTERY = "battery_level"
