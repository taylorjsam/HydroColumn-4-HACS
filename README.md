# HydroColumn-4-HACS

Native Home Assistant custom integration for HydroColumn-4 hydroponics controllers.
It uses Home Assistant's MQTT integration for real-time retained sensor/status topics
and local HTTP for slow status/history/config checks.

## Status

Initial scaffold. The integration defines the config flow, MQTT-backed entities, HTTP
coordinator, manual dose service, and a one-click Lovelace dashboard exporter.

## Install

1. Install and configure Home Assistant's MQTT integration first.
2. Copy this repository into HACS as a custom repository, or copy
   `custom_components/hydrocolumn` into your Home Assistant `custom_components`
   directory.
3. Restart Home Assistant.
4. Add the HydroColumn integration from Settings > Devices & services.

## Setup Fields

- Device ID: firmware ID such as `hydrocolumn-a1b2c3`
- Device IP or hostname: leave blank during setup to try `{device_id}.local`
- HTTP username/password: credentials used by the controller's REST API

MQTT broker settings are intentionally not collected here. HydroColumn publishes and
subscribes through Home Assistant's MQTT integration.

## Dashboard Export

After setup, press the `Export Dashboard` button entity. It writes a populated YAML
dashboard under `/config/dashboards` and creates a persistent notification with the
`configuration.yaml` Lovelace registration block.

## Manual Dose Service

```yaml
service: hydrocolumn.manual_dose
data:
  device_id: hydrocolumn-a1b2c3
  pump: 1
  seconds: 10
```

The integration validates pump `1` through `5`, caps duration to `1` through `30`
seconds, blocks while flood/leak is active, blocks while the device is offline, and
holds a dose lock for the requested run window.
