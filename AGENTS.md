# HydroColumn — Home Assistant Integration

## Master Build Context · `custom_components/hydrocolumn`

Load this file at the start of any HA integration build, review, or debug session.
Also load `HC4-ESP32-Firmware-AGENTS.md` when cross-referencing firmware behavior.

-----

## Integration Purpose

This is a native Home Assistant custom integration (`custom_components/hydrocolumn`) that
surfaces all HydroColumn-4 sensor data, status, and controls as first-class HA entities.
Notifications flow through the HA Companion app — no third-party push service needed.

**What this is NOT:**

- Not a standalone MQTT → HA bridge (native MQTT integration handles transport)
- Not an MQTT auto-discovery config (we own the entity definitions for full control)
- Not a cloud integration (LAN-only, no external API keys)

-----

## HydroColumn Firmware Context (Distilled)

> This section summarizes the ESP32 firmware that this integration talks to.
> For full detail, see `HC4-ESP32-Firmware-AGENTS.md`.

### Device Identity

Each unit has a unique device ID from its MAC address:

```
device_id = "hydrocolumn-{last 6 MAC chars}"   # e.g. hydrocolumn-a1b2c3
```

All MQTT topics and mDNS hostnames use this ID. The human name (“Cabinet 1”) is
separate, stored in NVS, and reflected in the `device_name` status field.

### Transport Layer

- **MQTT** — real-time sensor data, status, control commands. Published every 60s
  (normal) or 30s (post-dose, for 10 minutes after any dose). Retained messages used
  for all sensors and status so HA gets current state immediately on subscribe.
- **HTTP REST** — configuration changes, calibration, manual commands, history pull.
  Basic Auth required on all endpoints. Base URL: `http://{device_ip}/` or
  `http://hydrocolumn-{id}.local/`.
- **LWT** — `hydroponics/{device_id}/status/online` carries `"offline"` as Last Will;
  firmware publishes `"online"` on connect. Integration must treat `"offline"` as
  device unavailable and mark all entities unavailable.

### MQTT Topic Map (Full)

All topics prefixed with `hydroponics/{device_id}/`:

|Suffix                       |Direction|Payload                                             |Notes                                  |
|-----------------------------|---------|----------------------------------------------------|---------------------------------------|
|`sensors/ec`                 |ESP32→HA |`{"value": 1.82, "unit": "mS/cm", "ts": 1718123456}`|Retained                               |
|`sensors/ph`                 |ESP32→HA |`{"value": 6.1, "unit": "pH", "ts": ...}`           |Retained                               |
|`sensors/water_temp`         |ESP32→HA |`{"value": 22.4, "unit": "°C", "ts": ...}`          |Retained                               |
|`sensors/air_temp`           |ESP32→HA |`{"value": 24.1, "unit": "°C", "ts": ...}`          |Retained                               |
|`sensors/air_humidity`       |ESP32→HA |`{"value": 58.3, "unit": "%", "ts": ...}`           |Retained                               |
|`sensors/water_level_gallons`|ESP32→HA |`{"value": 18.5, "unit": "gal", "ts": ...}`         |Retained                               |
|`sensors/water_level_pct`    |ESP32→HA |`{"value": 68.5, "unit": "%", "ts": ...}`           |Retained                               |
|`sensors/flood`              |ESP32→HA |`"triggered"` or `"clear"`                          |Retained                               |
|`status/fault`               |ESP32→HA |`"ok"` or fault description string                  |Retained                               |
|`status/online`              |ESP32→HA |`"online"` / `"offline"` (LWT)                      |Retained                               |
|`status/dosing_mode`         |ESP32→HA |`"medium/late_growth"`                              |Retained                               |
|`status/lights_relay`        |ESP32→HA |`"on"` / `"off"`                                    |ESP32 output intent, not physical state|
|`status/circulation_relay`   |ESP32→HA |`"on"` / `"off"`                                    |ESP32 output intent, not physical state|
|`status/dosing_pump_1`       |ESP32→HA |`"idle"` / `"running"` / `"fault"`                  |Retained, repeat for 2–5               |
|`status/solution_remaining_1`|ESP32→HA |`{"value": 312, "unit": "ml"}`                      |Retained, repeat for 2–5               |
|`alerts/low_solution_1`      |ESP32→HA |`"true"` / `"false"`                                |Retained, repeat for 2–5               |
|`alerts/low_water`           |ESP32→HA |`"true"` / `"false"`                                |Retained                               |
|`alerts/ec_out_of_range`     |ESP32→HA |`"true"` / `"false"`                                |Retained                               |
|`alerts/ph_out_of_range`     |ESP32→HA |`"true"` / `"false"`                                |Retained                               |
|`control/dose_manual/{1-5}`  |HA→ESP32 |`{"seconds": 10}`                                   |QoS 1                                  |
|`control/reset_fault`        |HA→ESP32 |`"reset"`                                           |QoS 1                                  |
|`control/refill/{1-5}`       |HA→ESP32 |`"refill"`                                          |QoS 1                                  |
|`config/ec_target`           |HA→ESP32 |`"1.8"`                                             |QoS 1, retained                        |
|`config/ph_target_low`       |HA→ESP32 |`"5.8"`                                             |QoS 1, retained                        |
|`config/ph_target_high`      |HA→ESP32 |`"6.2"`                                             |QoS 1, retained                        |
|`config/dosing_mode`         |HA→ESP32 |`"medium/late_growth"`                              |QoS 1, retained                        |
|`config/auto_nutrient_dosing`|HA→ESP32 |`"true"` / `"false"`                                |QoS 1, retained                        |
|`config/auto_ph_dosing`      |HA→ESP32 |`"true"` / `"false"`                                |QoS 1, retained                        |

### HTTP API (used for config + history, not real-time)

```
GET  /api/sensors             → full sensor JSON snapshot
GET  /api/status              → system status + build_id + ip_address
GET  /api/config              → current config JSON
POST /api/config              → update config (JSON body)
GET  /api/history             → ring buffer of recent sensor readings (60 records)
POST /api/dose/{1-5}          → manual dose: {"seconds": N}  (max 30)
POST /api/reset_fault         → clear latching fault
POST /api/refill/{1-5}        → mark bottle refilled
POST /api/calibrate/pump/{1-5} → store pump calibration
```

All endpoints require HTTP Basic Auth. Return `{"ok": true/false}`.

### Safety States the Integration Must Respect

- **Leak/flood fault**: latching — requires explicit reset, never auto-clears
- **3-way physical switches**: ESP32 cannot read actual device state; relay topics
  reflect ESP32 *output intent* only. Do NOT label HA entities as “Lights On” — use
  “Light Relay Output” or similar to avoid implying physical certainty.
- **No simultaneous dosing pumps**: never send two `dose_manual` commands concurrently
- **Manual dose cap**: firmware enforces 30s max, but integration should also cap at 30s

-----

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Home Assistant                                          │
│                                                          │
│  custom_components/hydrocolumn/                          │
│    ├── config_flow.py   ← UI setup: device ID, broker    │
│    ├── coordinator.py   ← HTTP poll (60s) for history    │
│    ├── mqtt.py          ← MQTT subscribe/publish via     │
│    │                       hass.components.mqtt          │
│    ├── sensor.py        ← Sensor entities                │
│    ├── binary_sensor.py ← Binary sensor entities         │
│    ├── switch.py        ← Toggle entities                │
│    ├── number.py        ← Numeric config entities        │
│    ├── select.py        ← Mode/stage selectors           │
│    └── button.py        ← Action button entities         │
│                                                          │
│  HA MQTT Integration (Mosquitto add-on)                  │
│    └── handles broker connection + subscriptions         │
│                                                          │
│  HA Companion App (iOS)                                  │
│    └── receives push notifications from automations      │
└─────────────────────────────────────────────────────────┘
           ↕ MQTT (retained, QoS 0/1)
           ↕ HTTP (config, history, commands)
┌─────────────────────────────────────────────────────────┐
│  ESP32-S3  HydroColumn-{id}                             │
│  hydrocolumn-{id}.local                                 │
└─────────────────────────────────────────────────────────┘
```

**MQTT transport is via `hass.components.mqtt`** — the integration does NOT manage
its own broker connection. This means:

- HA’s Mosquitto add-on must be installed and running
- Config flow must validate MQTT is available before completing setup
- All subscriptions use `async_subscribe()` from the HA MQTT component

**HTTP is via `aiohttp`** — use `hass.helpers.aiohttp_client.async_get_clientsession()`
for connection pooling. Never create bare `aiohttp.ClientSession()` instances.

-----

## Repository Layout

```
custom_components/hydrocolumn/
├── __init__.py          ← async_setup_entry, async_unload_entry, services
├── manifest.json        ← integration metadata, requirements
├── config_flow.py       ← ConfigFlow + OptionsFlow
├── const.py             ← DOMAIN, platform list, topic templates, defaults
├── coordinator.py       ← HydroColumnCoordinator (DataUpdateCoordinator)
├── mqtt.py              ← HydroColumnMQTT: subscribe/publish helpers
├── entity_base.py       ← HydroColumnEntity base class
├── sensor.py            ← async_setup_entry, all sensor entity classes
├── binary_sensor.py     ← async_setup_entry, all binary sensor classes
├── switch.py            ← async_setup_entry, auto-dosing toggle switches
├── number.py            ← async_setup_entry, EC/pH numeric config entities
├── select.py            ← async_setup_entry, dosing mode + growth stage
├── button.py            ← async_setup_entry, reset fault + refill buttons
├── strings.json         ← translatable UI strings
├── translations/
│   └── en.json          ← English strings for config flow + entity names
└── services.yaml        ← custom service definitions (manual dose)
```

-----

## File Specifications

### `manifest.json`

```json
{
  "domain": "hydrocolumn",
  "name": "HydroColumn",
  "version": "0.1.0",
  "config_flow": true,
  "documentation": "https://github.com/yourrepo/hydrocolumn",
  "requirements": [],
  "dependencies": ["mqtt"],
  "codeowners": [],
  "iot_class": "local_push"
}
```

- `"iot_class": "local_push"` — data arrives via MQTT push, no cloud
- `"dependencies": ["mqtt"]` — declares hard dependency on HA MQTT integration

### `const.py`

Define all constants here. Never hardcode strings in entity files.

```python
DOMAIN = "hydrocolumn"
PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "select", "button"]

CONF_DEVICE_ID = "device_id"
CONF_DEVICE_IP = "device_ip"
CONF_TOPIC_PREFIX = "topic_prefix"  # e.g. "hydroponics/hydrocolumn-a1b2c3"

DEFAULT_TOPIC_PREFIX_TEMPLATE = "hydroponics/{device_id}"
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 300  # seconds, for HTTP history poll

# Solution names — matches pump channel assignment
SOLUTION_NAMES = {
    1: "FloraMicro",
    2: "FloraGro",
    3: "FloraBloom",
    4: "pH Down",
    5: "pH Up",
}

DOSING_MODES = [
    "light/early_growth", "light/late_growth", "light/early_bloom", "light/mid_late_bloom",
    "medium/early_growth", "medium/late_growth", "medium/early_bloom", "medium/mid_late_bloom",
    "aggressive/early_growth", "aggressive/late_growth", "aggressive/early_bloom",
    "aggressive/mid_late_bloom", "flush",
]
```

### `config_flow.py`

Config flow collects:

1. **Device ID** — e.g. `hydrocolumn-a1b2c3` (from the device’s web UI footer or mDNS)
1. **Device IP** — for HTTP API; try resolving `{device_id}.local` as default
1. **HTTP Basic Auth username/password** — required by all firmware REST endpoints;
   these are device credentials, not MQTT broker credentials
1. **Verify connectivity** — attempt `GET /api/status` with Basic Auth before completing
1. **Verify MQTT** — check `hass.components.mqtt` is loaded; fail with user-friendly
   error if not

OptionsFlow allows changing the device IP (in case it changes after DHCP renewal)
without re-pairing the integration.

Do NOT collect MQTT broker settings in the config flow — the integration uses HA’s
already-configured MQTT integration. If MQTT isn’t set up, show a clear error
directing the user to install the Mosquitto add-on first.

### `coordinator.py`

`HydroColumnCoordinator(DataUpdateCoordinator)` polls the HTTP API on a slow interval
(default 5 minutes) for data that isn’t pushed via MQTT:

- Sensor history ring buffer (`/api/history`) for HA statistics
- Runtime counters, calibration state, bottle totals (`/api/status`)

Real-time entity state comes exclusively from MQTT subscriptions — the coordinator
is NOT the primary data source for sensor values. Do not poll `/api/sensors` on the
coordinator cycle; MQTT handles that.

### `entity_base.py`

```python
class HydroColumnEntity(Entity):
    """Base class for all HydroColumn entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False  # all updates come from MQTT callbacks

    def __init__(self, coordinator, device_id, device_name):
        self._coordinator = coordinator
        self._device_id = device_id
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="HydroColumn",
            model="HC-4",
            sw_version=coordinator.data.get("build_id"),
            configuration_url=f"http://{coordinator.device_ip}/",
        )

    @property
    def device_info(self):
        return self._device_info

    @property
    def available(self):
        return self._coordinator.online  # driven by LWT topic
```

All entities must override `available` based on the LWT online state — when the
device publishes `"offline"` to the LWT topic, all entities become unavailable.

-----

## Entity Catalog

### Sensors (`sensor.py`)

|Entity Name         |MQTT Topic Suffix            |Unit |Device Class |State Class  |
|--------------------|-----------------------------|-----|-------------|-------------|
|EC                  |`sensors/ec`                 |mS/cm|—            |`measurement`|
|pH                  |`sensors/ph`                 |pH   |—            |`measurement`|
|Water Temperature   |`sensors/water_temp`         |°C   |`temperature`|`measurement`|
|Air Temperature     |`sensors/air_temp`           |°C   |`temperature`|`measurement`|
|Air Humidity        |`sensors/air_humidity`       |%    |`humidity`   |`measurement`|
|Water Level         |`sensors/water_level_gallons`|gal  |`volume`     |`measurement`|
|Water Level (%)     |`sensors/water_level_pct`    |%    |—            |`measurement`|
|FloraMicro Remaining|`status/solution_remaining_1`|mL   |`volume`     |`measurement`|
|FloraGro Remaining  |`status/solution_remaining_2`|mL   |`volume`     |`measurement`|
|FloraBloom Remaining|`status/solution_remaining_3`|mL   |`volume`     |`measurement`|
|pH Down Remaining   |`status/solution_remaining_4`|mL   |`volume`     |`measurement`|
|pH Up Remaining     |`status/solution_remaining_5`|mL   |`volume`     |`measurement`|
|Dosing Mode         |`status/dosing_mode`         |—    |`enum`       |—            |
|Pump 1 Status       |`status/dosing_pump_1`       |—    |`enum`       |—            |
|Pump 2 Status       |`status/dosing_pump_2`       |—    |`enum`       |—            |
|Pump 3 Status       |`status/dosing_pump_3`       |—    |`enum`       |—            |
|Pump 4 Status       |`status/dosing_pump_4`       |—    |`enum`       |—            |
|Pump 5 Status       |`status/dosing_pump_5`       |—    |`enum`       |—            |

Parse JSON payloads: extract `value` field. Fall back to raw string for plain scalar
topics. Always set `_attr_state = None` (unavailable) on parse error.

### Binary Sensors (`binary_sensor.py`)

|Entity Name             |MQTT Topic Suffix         |Device Class  |On Payload         |Alert Priority|
|------------------------|--------------------------|--------------|-------------------|--------------|
|Flood / Leak            |`sensors/flood`           |`moisture`    |`"triggered"`      |CRITICAL      |
|Fault Active            |`status/fault`            |`problem`     |any string ≠ `"ok"`|HIGH          |
|Online                  |`status/online`           |`connectivity`|`"online"`         |—             |
|Light Relay Output      |`status/lights_relay`     |`light`       |`"on"`             |—             |
|Circulation Relay Output|`status/circulation_relay`|`running`     |`"on"`             |—             |
|Low Water               |`alerts/low_water`        |`moisture`    |`"true"`           |HIGH          |
|EC Out of Range         |`alerts/ec_out_of_range`  |`problem`     |`"true"`           |MEDIUM        |
|pH Out of Range         |`alerts/ph_out_of_range`  |`problem`     |`"true"`           |MEDIUM        |
|Low FloraMicro          |`alerts/low_solution_1`   |`problem`     |`"true"`           |LOW           |
|Low FloraGro            |`alerts/low_solution_2`   |`problem`     |`"true"`           |LOW           |
|Low FloraBloom          |`alerts/low_solution_3`   |`problem`     |`"true"`           |LOW           |
|Low pH Down             |`alerts/low_solution_4`   |`problem`     |`"true"`           |LOW           |
|Low pH Up               |`alerts/low_solution_5`   |`problem`     |`"true"`           |LOW           |

**Relay entity labeling:** Light and Circulation entities must use “Light Relay Output”
and “Circulation Relay Output” naming — NOT “Lights On/Off”. The 3-way physical
override switches mean ESP32 output intent ≠ actual device state. Labels must
reflect this limitation.

### Switches (`switch.py`)

|Entity Name         |MQTT Config Topic            |On Payload|Off Payload|
|--------------------|-----------------------------|----------|-----------|
|Auto Nutrient Dosing|`config/auto_nutrient_dosing`|`"true"`  |`"false"`  |
|Auto pH Dosing      |`config/auto_ph_dosing`      |`"true"`  |`"false"`  |

On toggle: publish to config topic with QoS 1, retain=True.
Optimistic update: set state immediately, revert if no echo back within 5s.

### Numbers (`number.py`)

|Entity Name   |MQTT Config Topic      |Min|Max|Step|Unit |
|--------------|-----------------------|---|---|----|-----|
|EC Target     |`config/ec_target`     |0.0|3.5|0.1 |mS/cm|
|pH Target Low |`config/ph_target_low` |4.5|7.5|0.1 |pH   |
|pH Target High|`config/ph_target_high`|4.5|7.5|0.1 |pH   |

Validate `ph_target_low < ph_target_high` before publishing. Reject silently if
constraint violated — add a warning log entry.

On change: publish string representation to config topic with QoS 1, retain=True.

### Selects (`select.py`)

|Entity Name|MQTT Config Topic   |Options                            |
|-----------|--------------------|-----------------------------------|
|Dosing Mode|`config/dosing_mode`|`DOSING_MODES` list from `const.py`|

On change: publish selected value to config topic with QoS 1, retain=True.
Current value reflects last received value from `status/dosing_mode` topic.

### Buttons (`button.py`)

|Entity Name      |Action                                            |Notes                            |
|-----------------|--------------------------------------------------|---------------------------------|
|Reset Fault      |Publish `"reset"` to `control/reset_fault` (QoS 1)|Only enabled when fault is active|
|Refill FloraMicro|Publish `"refill"` to `control/refill/1` (QoS 1)  |—                                |
|Refill FloraGro  |Publish `"refill"` to `control/refill/2` (QoS 1)  |—                                |
|Refill FloraBloom|Publish `"refill"` to `control/refill/3` (QoS 1)  |—                                |
|Refill pH Down   |Publish `"refill"` to `control/refill/4` (QoS 1)  |—                                |
|Refill pH Up     |Publish `"refill"` to `control/refill/5` (QoS 1)  |—                                |

### Custom Service — `hydrocolumn.manual_dose`

Registered in `services.yaml`. Allows automations to trigger a timed manual dose:

```yaml
service: hydrocolumn.manual_dose
data:
  device_id: hydrocolumn-a1b2c3
  pump: 1           # 1–5
  seconds: 10       # 1–30
```

Implementation: publishes `{"seconds": N}` to `control/dose_manual/{pump}` QoS 1.
Validate `pump` is 1–5 and `seconds` is 1–30. Log and raise `ServiceValidationError`
on invalid input. Never fire if flood fault is active.

-----

## Notification Architecture

All notifications flow through HA automations → HA Companion app (iOS push).
The integration itself does NOT send notifications directly — it exposes the right
binary sensor and sensor entities so automations can fire on state changes.

### Recommended Automation Triggers

|Trigger Entity                       |Condition                             |Notification Priority    |Action                                             |
|-------------------------------------|--------------------------------------|-------------------------|---------------------------------------------------|
|`binary_sensor.flood_leak` → `on`    |—                                     |**Critical** (bypass DND)|“LEAK DETECTED — check cabinet immediately”        |
|`binary_sensor.fault_active` → `on`  |—                                     |High                     |“HydroColumn fault: {state_attr fault_description}”|
|`binary_sensor.low_water` → `on`     |—                                     |High                     |“Water level low — refill reservoir”               |
|`sensor.ec`                          |value outside target range for >30 min|Medium                   |“EC drifting: {value} mS/cm (target {target})”     |
|`sensor.ph`                          |value outside target range for >30 min|Medium                   |“pH drifting: {value} (target {low}–{high})”       |
|`binary_sensor.low_floramicro` → `on`|—                                     |Low                      |“FloraMicro running low — {remaining} mL remaining”|
|(repeat for other solutions)         |                                      |                         |                                                   |

### iOS Critical Alert Setup

For flood/leak and fault notifications, use `apns-collapse-id` and `push.sound.critical`
in the HA notification service call:

```yaml
service: notify.mobile_app_your_phone
data:
  title: "⚠️ HydroColumn Leak Detected"
  message: "Flood sensor triggered. All pumps stopped."
  data:
    push:
      sound:
        name: default
        critical: 1
        volume: 1.0
    apns_collapse_id: hydrocolumn_leak
```

### Automation Best Practices

- Use `for:` duration on EC/pH drift triggers — do not alert on a single out-of-range
  reading. 30-minute sustained drift is the right threshold.
- Flood and fault alerts should fire immediately with no delay.
- Low solution alerts should fire once, not on every state evaluation. Use
  `trigger_variables` or a `counter` helper to suppress repeat notifications until
  the bottle is refilled.
- Group all HydroColumn automations under a single label for easy enable/disable.

-----

## HA Dashboard (Lovelace)

The integration should ship a `dashboard.yaml` in the repo (not auto-registered,
user imports manually). Recommended card layout:

### Primary Cards

- **Gauge** cards for EC and pH with color zones (ok/warn/critical)
- **Statistic graph** cards for EC, pH, water temp over 24h
- **Entities** card for water level + solution remaining per pump
- **Mushroom chip** cards for fault and flood binary sensors (red when active)
- **Button** cards for Reset Fault and Refill actions

### Status Section

- Light relay output intent
- Circulation relay output intent
- Pump 1–5 status (idle/running/fault)
- Auto nutrient dosing toggle
- Auto pH dosing toggle
- Online/offline indicator

### Config Section (collapsible)

- EC target number
- pH target low/high numbers
- Dosing mode select

-----

## Development Environment

### Tooling

- **Package management:** `uv` — never use `pip` directly
- **Python version:** 3.12+ (pin in `pyproject.toml`)
- **HA version target:** 2024.1+ (use `async_setup_entry`, avoid deprecated APIs)
- **Dev environment:** `hass-custom-component-scaffold` or manual HACS structure

### Setup

```bash
uv init hydrocolumn-ha
uv add homeassistant pytest-homeassistant-custom-component pytest-asyncio aiohttp
uv run pytest tests/
```

### Local Testing

- Use `homeassistant` PyPI package for type hints and test fixtures
- `pytest-homeassistant-custom-component` for integration test helpers
- Run against a real HA dev instance via VS Code devcontainer for end-to-end

### Required `pyproject.toml` fields

```toml
[project]
name = "hydrocolumn-ha"
requires-python = ">=3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

-----

## Coding Standards

### General Python

- All async — no blocking calls anywhere. `asyncio`, `aiohttp`, HA’s async helpers.
- Type hints on all public methods and class attributes
- `logging.getLogger(__name__)` — never use `print()` in integration code
- No bare `except:` — always catch specific exceptions, log with context

### HA-Specific Rules

- Never import from `homeassistant.components.*` at module level — use
  `hass.components.*` at runtime to avoid import ordering issues
- Always use `hass.helpers.aiohttp_client.async_get_clientsession()` for HTTP —
  never create bare `ClientSession`
- Register all subscriptions and listeners in `async_setup_entry`, clean up in
  `async_unload_entry`. Use `entry.async_on_unload()` for cleanup callbacks.
- Entities must NOT store raw MQTT payload — parse to typed Python values immediately
- Call `self.async_write_ha_state()` after every state update in MQTT callbacks
- Use `@callback` decorator on synchronous functions called from async context

### MQTT Subscription Pattern

```python
async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    prefix = entry.data[CONF_TOPIC_PREFIX]

    entities = [ECSensor(coordinator, prefix), ...]
    async_add_entities(entities)

    # Each entity registers its own subscription
    for entity in entities:
        entry.async_on_unload(
            await hass.components.mqtt.async_subscribe(
                entity.topic, entity.async_message_received
            )
        )
```

### HTTP Request Pattern

```python
async def _async_fetch_status(self) -> dict:
    session = async_get_clientsession(self.hass)
    try:
        async with asyncio.timeout(10):
            resp = await session.get(
                f"http://{self._ip}/api/status",
                auth=aiohttp.BasicAuth(self._username, self._password),
            )
            resp.raise_for_status()
            return await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.warning("HTTP fetch failed for %s: %s", self._device_id, err)
        return {}
```

### Secrets

- Device IP, device ID, HTTP credentials stored in HA config entry `data` dict
- Never log credentials — use `entry.data[CONF_PASSWORD]` only at auth time
- MQTT credentials are HA’s own — this integration never handles broker auth directly

-----

## Code Review Process

When asked to review this integration, follow these steps exactly.

### Step 1 — Load both AGENTS files

Read this file AND `HC4-ESP32-Firmware-AGENTS.md` before opening any source file.
The firmware spec is ground truth for topic names, payload formats, and safety
constraints. Every finding must trace to a specific spec violation.

### Step 2 — Read every source file

Read all files under `custom_components/hydrocolumn/`. Do not skip any.
Issues frequently cross file boundaries.

Files to always check:

- `manifest.json` — version, dependencies, iot_class
- `const.py` — topic templates match firmware spec, solution names match pump assignments
- `config_flow.py` — validates MQTT available, validates HTTP reachable, no secrets stored
- `coordinator.py` — uses `async_get_clientsession`, handles timeout/error gracefully
- `mqtt.py` — all subscriptions cleaned up on unload, no blocking calls
- `entity_base.py` — `available` property driven by LWT state
- `sensor.py` — all sensors from entity catalog present, JSON parsed correctly
- `binary_sensor.py` — relay entities use correct “output intent” language, flood is critical class
- `switch.py` — optimistic update pattern, reverts on no echo
- `number.py` — pH low < pH high validated before publish
- `__init__.py` — manual_dose validates pump 1–5, seconds 1–30, blocks on flood fault
- `button.py` — reset/refill buttons publish only the specified control topics
- `services.yaml` — manual_dose service documented with correct fields

### Step 3 — Cross-file consistency checks

|Check         |What to verify                                                                    |
|--------------|----------------------------------------------------------------------------------|
|Topic names   |Every MQTT topic in entity files matches the topic map in this AGENTS file exactly|
|LWT handling  |All entities return `False` for `available` when coordinator.online is False      |
|Relay labeling|No entity is named “Lights On/Off” or implies physical device state               |
|Flood safety  |`manual_dose` service refuses to fire when flood binary sensor is `on`            |
|JSON parsing  |All sensor entities handle malformed JSON gracefully (log warning, set state None)|
|Cleanup       |Every `async_subscribe` result stored and passed to `entry.async_on_unload`       |
|HTTP sessions |No bare `aiohttp.ClientSession()` anywhere — must use HA helper                   |
|Secrets       |No credentials hardcoded or logged                                                |
|Type hints    |All public methods typed                                                          |

### Step 4 — Classify and write findings to `REVIEW.md`

|Priority    |Criteria                                                                                          |
|------------|--------------------------------------------------------------------------------------------------|
|**CRITICAL**|Safety violation (flood fault bypass, leak not triggering unavailable), data loss, credential leak|
|**HIGH**    |Entity missing, wrong device class, MQTT subscription not cleaned up                              |
|**MEDIUM**  |Wrong unit, incorrect payload parsing, edge case failure                                          |
|**LOW**     |Naming inconsistency, log verbosity, cosmetic                                                     |

Each finding: priority label, file + line, what spec says, what code does, minimal fix.

### Step 5 — After fixes, re-verify

Re-read every changed file. Confirm fix matches spec. Check for adjacency regressions.
Remove resolved items from `REVIEW.md`. Increment integration version in `manifest.json`
for any user-visible change.

-----

## Open Items / Pending Decisions

|Item                             |Status                                                                                            |
|---------------------------------|--------------------------------------------------------------------------------------------------|
|RS485 register map for EC/pH unit|Not yet obtained — integration uses whatever firmware exposes on MQTT                             |
|PZEM-016 power monitoring topics |Planned addition to firmware — add `sensors/power_w`, `sensors/energy_kwh` when firmware adds them|
|InfluxDB long-term history       |TBD — route via HA recorder or direct MQTT bridge                                                 |
|Dashboard YAML                   |To be written after entity set is finalized                                                       |
|`apns-collapse-id` keys          |Settle final IDs once notification automation set is complete                                     |
