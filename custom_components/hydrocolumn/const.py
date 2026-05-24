"""Constants for the HydroColumn integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

DOMAIN = "hydrocolumn"
RUNTIME_COORDINATOR = "coordinator"
RUNTIME_MQTT = "mqtt"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]

CONF_DEVICE_ID = "device_id"
CONF_DEVICE_IP = "device_ip"
CONF_TOPIC_PREFIX = "topic_prefix"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_TOPIC_PREFIX_TEMPLATE = "hydroponics/{device_id}"
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 300
DEFAULT_HTTP_TIMEOUT = 10
DEFAULT_USERNAME = "admin"

SERVICE_MANUAL_DOSE = "manual_dose"
SERVICE_FIELD_DEVICE_ID = "device_id"
SERVICE_FIELD_PUMP = "pump"
SERVICE_FIELD_SECONDS = "seconds"

ATTR_FAULT_DESCRIPTION = "fault_description"
ATTR_LAST_SEEN_TS = "last_seen_ts"
ATTR_PAYLOAD_UNIT = "payload_unit"
ATTR_DASHBOARD_PATH = "dashboard_path"
ATTR_REGISTRATION_SNIPPET = "registration_snippet"
HA_ATTR_DEVICE_CLASS = "device_class"
HA_ATTR_MAX = "max"
HA_ATTR_MIN = "min"
HA_ATTR_MODE = "mode"
HA_ATTR_OPTIONS = "options"
HA_ATTR_STATE_CLASS = "state_class"
HA_ATTR_STEP = "step"
HA_ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"
NUMBER_MODE_BOX = "box"

TOPIC_SENSOR_EC = "sensors/ec"
TOPIC_SENSOR_PH = "sensors/ph"
TOPIC_SENSOR_WATER_TEMP = "sensors/water_temp"
TOPIC_SENSOR_AIR_TEMP = "sensors/air_temp"
TOPIC_SENSOR_AIR_HUMIDITY = "sensors/air_humidity"
TOPIC_SENSOR_WATER_LEVEL_GALLONS = "sensors/water_level_gallons"
TOPIC_SENSOR_WATER_LEVEL_PCT = "sensors/water_level_pct"
TOPIC_SENSOR_FLOOD = "sensors/flood"
TOPIC_STATUS_FAULT = "status/fault"
TOPIC_STATUS_ONLINE = "status/online"
TOPIC_STATUS_DOSING_MODE = "status/dosing_mode"
TOPIC_STATUS_LIGHTS_RELAY = "status/lights_relay"
TOPIC_STATUS_CIRCULATION_RELAY = "status/circulation_relay"
TOPIC_STATUS_DOSING_PUMP = "status/dosing_pump_{pump}"
TOPIC_STATUS_SOLUTION_REMAINING = "status/solution_remaining_{pump}"
TOPIC_ALERT_LOW_SOLUTION = "alerts/low_solution_{pump}"
TOPIC_ALERT_LOW_WATER = "alerts/low_water"
TOPIC_ALERT_EC_OUT_OF_RANGE = "alerts/ec_out_of_range"
TOPIC_ALERT_PH_OUT_OF_RANGE = "alerts/ph_out_of_range"
TOPIC_CONTROL_DOSE_MANUAL = "control/dose_manual/{pump}"
TOPIC_CONTROL_RESET_FAULT = "control/reset_fault"
TOPIC_CONTROL_REFILL = "control/refill/{pump}"
TOPIC_CONFIG_EC_TARGET = "config/ec_target"
TOPIC_CONFIG_PH_TARGET_LOW = "config/ph_target_low"
TOPIC_CONFIG_PH_TARGET_HIGH = "config/ph_target_high"
TOPIC_CONFIG_DOSING_MODE = "config/dosing_mode"
TOPIC_CONFIG_AUTO_NUTRIENT_DOSING = "config/auto_nutrient_dosing"
TOPIC_CONFIG_AUTO_PH_DOSING = "config/auto_ph_dosing"

PAYLOAD_ONLINE = "online"
PAYLOAD_OFFLINE = "offline"
PAYLOAD_ON = "on"
PAYLOAD_OFF = "off"
PAYLOAD_TRUE = "true"
PAYLOAD_FALSE = "false"
PAYLOAD_TRIGGERED = "triggered"
PAYLOAD_CLEAR = "clear"
PAYLOAD_OK = "ok"
PAYLOAD_RESET = "reset"
PAYLOAD_REFILL = "refill"

UNIT_EC = "mS/cm"
UNIT_PH = "pH"
UNIT_CELSIUS = "°C"
UNIT_PERCENT = "%"
UNIT_GALLONS = "gal"
UNIT_MILLILITERS = "mL"

DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_HUMIDITY = "humidity"
DEVICE_CLASS_VOLUME = "volume"
DEVICE_CLASS_ENUM = "enum"
DEVICE_CLASS_MOISTURE = "moisture"
DEVICE_CLASS_PROBLEM = "problem"
DEVICE_CLASS_CONNECTIVITY = "connectivity"
DEVICE_CLASS_LIGHT = "light"
DEVICE_CLASS_RUNNING = "running"
STATE_CLASS_MEASUREMENT = "measurement"

KEY_EC = "ec"
KEY_PH = "ph"
KEY_WATER_TEMP = "water_temperature"
KEY_AIR_TEMP = "air_temperature"
KEY_AIR_HUMIDITY = "air_humidity"
KEY_WATER_LEVEL = "water_level"
KEY_WATER_LEVEL_PCT = "water_level_pct"
KEY_DOSING_MODE_SENSOR = "dosing_mode_status"
KEY_FLOOD = "flood_leak"
KEY_FAULT_ACTIVE = "fault_active"
KEY_ONLINE = "online"
KEY_LIGHT_RELAY_OUTPUT = "light_relay_output"
KEY_CIRCULATION_RELAY_OUTPUT = "circulation_relay_output"
KEY_LOW_WATER = "low_water"
KEY_EC_OUT_OF_RANGE = "ec_out_of_range"
KEY_PH_OUT_OF_RANGE = "ph_out_of_range"
KEY_AUTO_NUTRIENT_DOSING = "auto_nutrient_dosing"
KEY_AUTO_PH_DOSING = "auto_ph_dosing"
KEY_EC_TARGET = "ec_target"
KEY_PH_TARGET_LOW = "ph_target_low"
KEY_PH_TARGET_HIGH = "ph_target_high"
KEY_DOSING_MODE_SELECT = "dosing_mode"
KEY_RESET_FAULT = "reset_fault"
KEY_EXPORT_DASHBOARD = "export_dashboard"

SOLUTION_NAMES = {
    1: "FloraMicro",
    2: "FloraGro",
    3: "FloraBloom",
    4: "pH Down",
    5: "pH Up",
}

DOSING_MODES = [
    "light/early_growth",
    "light/late_growth",
    "light/early_bloom",
    "light/mid_late_bloom",
    "medium/early_growth",
    "medium/late_growth",
    "medium/early_bloom",
    "medium/mid_late_bloom",
    "aggressive/early_growth",
    "aggressive/late_growth",
    "aggressive/early_bloom",
    "aggressive/mid_late_bloom",
    "flush",
]


@dataclass(frozen=True, slots=True)
class HydroColumnSensorDescription:
    """Static description for a HydroColumn sensor entity."""

    key: str
    name: str
    topic_suffix: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None
    value_type: type = float
    options: list[str] | None = None


@dataclass(frozen=True, slots=True)
class HydroColumnBinarySensorDescription:
    """Static description for a HydroColumn binary sensor entity."""

    key: str
    name: str
    topic_suffix: str
    on_payload: str
    device_class: str | None = None
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class HydroColumnSwitchDescription:
    """Static description for a HydroColumn switch entity."""

    key: str
    name: str
    topic_suffix: str
    icon: str


@dataclass(frozen=True, slots=True)
class HydroColumnNumberDescription:
    """Static description for a HydroColumn number entity."""

    key: str
    name: str
    topic_suffix: str
    native_min_value: float
    native_max_value: float
    native_step: float
    unit: str
    icon: str


@dataclass(frozen=True, slots=True)
class HydroColumnSelectDescription:
    """Static description for a HydroColumn select entity."""

    key: str
    name: str
    state_topic_suffix: str
    command_topic_suffix: str
    options: list[str]
    icon: str


@dataclass(frozen=True, slots=True)
class HydroColumnButtonDescription:
    """Static description for a HydroColumn button entity."""

    key: str
    name: str
    icon: str
    topic_suffix: str | None = None
    payload: str | None = None
    pump: int | None = None


SENSOR_DESCRIPTIONS: tuple[HydroColumnSensorDescription, ...] = (
    HydroColumnSensorDescription(
        KEY_EC,
        "EC",
        TOPIC_SENSOR_EC,
        UNIT_EC,
        state_class=STATE_CLASS_MEASUREMENT,
        icon="mdi:chart-bell-curve",
    ),
    HydroColumnSensorDescription(
        KEY_PH,
        "pH",
        TOPIC_SENSOR_PH,
        UNIT_PH,
        state_class=STATE_CLASS_MEASUREMENT,
        icon="mdi:ph",
    ),
    HydroColumnSensorDescription(
        KEY_WATER_TEMP,
        "Water Temperature",
        TOPIC_SENSOR_WATER_TEMP,
        UNIT_CELSIUS,
        DEVICE_CLASS_TEMPERATURE,
        STATE_CLASS_MEASUREMENT,
    ),
    HydroColumnSensorDescription(
        KEY_AIR_TEMP,
        "Air Temperature",
        TOPIC_SENSOR_AIR_TEMP,
        UNIT_CELSIUS,
        DEVICE_CLASS_TEMPERATURE,
        STATE_CLASS_MEASUREMENT,
    ),
    HydroColumnSensorDescription(
        KEY_AIR_HUMIDITY,
        "Air Humidity",
        TOPIC_SENSOR_AIR_HUMIDITY,
        UNIT_PERCENT,
        DEVICE_CLASS_HUMIDITY,
        STATE_CLASS_MEASUREMENT,
    ),
    HydroColumnSensorDescription(
        KEY_WATER_LEVEL,
        "Water Level",
        TOPIC_SENSOR_WATER_LEVEL_GALLONS,
        UNIT_GALLONS,
        DEVICE_CLASS_VOLUME,
        STATE_CLASS_MEASUREMENT,
        icon="mdi:waves-arrow-up",
    ),
    HydroColumnSensorDescription(
        KEY_WATER_LEVEL_PCT,
        "Water Level (%)",
        TOPIC_SENSOR_WATER_LEVEL_PCT,
        UNIT_PERCENT,
        state_class=STATE_CLASS_MEASUREMENT,
        icon="mdi:waves",
    ),
    HydroColumnSensorDescription(
        KEY_DOSING_MODE_SENSOR,
        "Dosing Mode",
        TOPIC_STATUS_DOSING_MODE,
        device_class=DEVICE_CLASS_ENUM,
        icon="mdi:sprout",
        value_type=str,
        options=DOSING_MODES,
    ),
)

SOLUTION_REMAINING_SENSOR_DESCRIPTIONS: tuple[
    HydroColumnSensorDescription, ...
] = tuple(
    HydroColumnSensorDescription(
        f"solution_remaining_{pump}",
        f"{name} Remaining",
        TOPIC_STATUS_SOLUTION_REMAINING.format(pump=pump),
        UNIT_MILLILITERS,
        DEVICE_CLASS_VOLUME,
        STATE_CLASS_MEASUREMENT,
        icon="mdi:bottle-tonic-outline",
    )
    for pump, name in SOLUTION_NAMES.items()
)

PUMP_STATUS_SENSOR_DESCRIPTIONS: tuple[HydroColumnSensorDescription, ...] = tuple(
    HydroColumnSensorDescription(
        f"dosing_pump_{pump}_status",
        f"Pump {pump} Status",
        TOPIC_STATUS_DOSING_PUMP.format(pump=pump),
        device_class=DEVICE_CLASS_ENUM,
        icon="mdi:pump",
        value_type=str,
        options=["idle", "running", "fault"],
    )
    for pump in SOLUTION_NAMES
)

BINARY_SENSOR_DESCRIPTIONS: tuple[HydroColumnBinarySensorDescription, ...] = (
    HydroColumnBinarySensorDescription(
        KEY_FLOOD,
        "Flood / Leak",
        TOPIC_SENSOR_FLOOD,
        PAYLOAD_TRIGGERED,
        DEVICE_CLASS_MOISTURE,
        "mdi:water-alert",
    ),
    HydroColumnBinarySensorDescription(
        KEY_FAULT_ACTIVE,
        "Fault Active",
        TOPIC_STATUS_FAULT,
        PAYLOAD_OK,
        DEVICE_CLASS_PROBLEM,
        "mdi:alert-octagon",
    ),
    HydroColumnBinarySensorDescription(
        KEY_ONLINE,
        "Online",
        TOPIC_STATUS_ONLINE,
        PAYLOAD_ONLINE,
        DEVICE_CLASS_CONNECTIVITY,
        "mdi:lan-connect",
    ),
    HydroColumnBinarySensorDescription(
        KEY_LIGHT_RELAY_OUTPUT,
        "Light Relay Output",
        TOPIC_STATUS_LIGHTS_RELAY,
        PAYLOAD_ON,
        DEVICE_CLASS_LIGHT,
        "mdi:lightbulb-on-outline",
    ),
    HydroColumnBinarySensorDescription(
        KEY_CIRCULATION_RELAY_OUTPUT,
        "Circulation Relay Output",
        TOPIC_STATUS_CIRCULATION_RELAY,
        PAYLOAD_ON,
        DEVICE_CLASS_RUNNING,
        "mdi:pump",
    ),
    HydroColumnBinarySensorDescription(
        KEY_LOW_WATER,
        "Low Water",
        TOPIC_ALERT_LOW_WATER,
        PAYLOAD_TRUE,
        DEVICE_CLASS_MOISTURE,
        "mdi:waves-arrow-down",
    ),
    HydroColumnBinarySensorDescription(
        KEY_EC_OUT_OF_RANGE,
        "EC Out of Range",
        TOPIC_ALERT_EC_OUT_OF_RANGE,
        PAYLOAD_TRUE,
        DEVICE_CLASS_PROBLEM,
        "mdi:chart-bell-curve-cumulative",
    ),
    HydroColumnBinarySensorDescription(
        KEY_PH_OUT_OF_RANGE,
        "pH Out of Range",
        TOPIC_ALERT_PH_OUT_OF_RANGE,
        PAYLOAD_TRUE,
        DEVICE_CLASS_PROBLEM,
        "mdi:ph",
    ),
)

LOW_SOLUTION_BINARY_SENSOR_DESCRIPTIONS: tuple[
    HydroColumnBinarySensorDescription, ...
] = tuple(
    HydroColumnBinarySensorDescription(
        f"low_solution_{pump}",
        f"Low {name}",
        TOPIC_ALERT_LOW_SOLUTION.format(pump=pump),
        PAYLOAD_TRUE,
        DEVICE_CLASS_PROBLEM,
        "mdi:bottle-tonic-outline",
    )
    for pump, name in SOLUTION_NAMES.items()
)

SWITCH_DESCRIPTIONS: tuple[HydroColumnSwitchDescription, ...] = (
    HydroColumnSwitchDescription(
        KEY_AUTO_NUTRIENT_DOSING,
        "Auto Nutrient Dosing",
        TOPIC_CONFIG_AUTO_NUTRIENT_DOSING,
        "mdi:flask-round-bottom",
    ),
    HydroColumnSwitchDescription(
        KEY_AUTO_PH_DOSING,
        "Auto pH Dosing",
        TOPIC_CONFIG_AUTO_PH_DOSING,
        "mdi:ph",
    ),
)

NUMBER_DESCRIPTIONS: tuple[HydroColumnNumberDescription, ...] = (
    HydroColumnNumberDescription(
        KEY_EC_TARGET,
        "EC Target",
        TOPIC_CONFIG_EC_TARGET,
        0.0,
        3.5,
        0.1,
        UNIT_EC,
        "mdi:chart-bell-curve",
    ),
    HydroColumnNumberDescription(
        KEY_PH_TARGET_LOW,
        "pH Target Low",
        TOPIC_CONFIG_PH_TARGET_LOW,
        4.5,
        7.5,
        0.1,
        UNIT_PH,
        "mdi:ph",
    ),
    HydroColumnNumberDescription(
        KEY_PH_TARGET_HIGH,
        "pH Target High",
        TOPIC_CONFIG_PH_TARGET_HIGH,
        4.5,
        7.5,
        0.1,
        UNIT_PH,
        "mdi:ph",
    ),
)

SELECT_DESCRIPTIONS: tuple[HydroColumnSelectDescription, ...] = (
    HydroColumnSelectDescription(
        KEY_DOSING_MODE_SELECT,
        "Dosing Mode",
        TOPIC_STATUS_DOSING_MODE,
        TOPIC_CONFIG_DOSING_MODE,
        DOSING_MODES,
        "mdi:sprout",
    ),
)

BUTTON_DESCRIPTIONS: tuple[HydroColumnButtonDescription, ...] = (
    HydroColumnButtonDescription(
        KEY_RESET_FAULT,
        "Reset Fault",
        "mdi:alert-octagon-outline",
        TOPIC_CONTROL_RESET_FAULT,
        PAYLOAD_RESET,
    ),
    HydroColumnButtonDescription(
        KEY_EXPORT_DASHBOARD,
        "Export Dashboard",
        "mdi:view-dashboard-edit",
    ),
) + tuple(
    HydroColumnButtonDescription(
        f"refill_solution_{pump}",
        f"Refill {name}",
        "mdi:bottle-tonic-plus-outline",
        TOPIC_CONTROL_REFILL.format(pump=pump),
        PAYLOAD_REFILL,
        pump,
    )
    for pump, name in SOLUTION_NAMES.items()
)
