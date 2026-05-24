# HydroColumn Agent Memory

This file captures project gotchas that are useful beyond the root `AGENTS.md`.

- The repo currently does not include `HC4-ESP32-Firmware-AGENTS.md`. Until it is added, use the firmware contract distilled in `AGENTS.md` as the local source of truth.
- The firmware HTTP API requires Basic Auth, so the config flow must collect and store HTTP username/password even though MQTT credentials are never handled by this integration.
- The project standard says not to import from `homeassistant.components.*` at module level. The initial scaffold therefore uses generic HA entities with the platform service methods/properties implemented directly.
- LWT drives entity availability. In this scaffold, even utility buttons follow device online state unless a future design explicitly exempts non-device actions.
- Dashboard export must resolve live entity IDs from Home Assistant's entity registry. Do not guess entity IDs from names, because entity IDs can be customized by users.
- Runtime dashboard exports belong under `/config/dashboards`. The packaged dashboard YAML is only a reference template.
- Manual dosing is guarded by pump range, 1-30 second duration, LWT online state, the flood/leak safety state, and an integration-level lock held for the requested dose window to avoid overlapping pump runs.
