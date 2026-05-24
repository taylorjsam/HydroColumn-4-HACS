"""Button entities and dashboard export for HydroColumn."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DASHBOARD_PATH,
    ATTR_REGISTRATION_SNIPPET,
    BUTTON_DESCRIPTIONS,
    DOMAIN,
    KEY_AIR_HUMIDITY,
    KEY_AIR_TEMP,
    KEY_AUTO_NUTRIENT_DOSING,
    KEY_AUTO_PH_DOSING,
    KEY_CIRCULATION_RELAY_OUTPUT,
    KEY_DOSING_MODE_SELECT,
    KEY_DOSING_MODE_SENSOR,
    KEY_EC,
    KEY_EC_OUT_OF_RANGE,
    KEY_EC_TARGET,
    KEY_EXPORT_DASHBOARD,
    KEY_FAULT_ACTIVE,
    KEY_FLOOD,
    KEY_LIGHT_RELAY_OUTPUT,
    KEY_LOW_WATER,
    KEY_ONLINE,
    KEY_PH,
    KEY_PH_OUT_OF_RANGE,
    KEY_PH_TARGET_HIGH,
    KEY_PH_TARGET_LOW,
    KEY_RESET_FAULT,
    KEY_WATER_LEVEL,
    KEY_WATER_LEVEL_PCT,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    SOLUTION_NAMES,
    HydroColumnButtonDescription,
)
from .coordinator import HydroColumnCoordinator
from .entity_base import HydroColumnEntity
from .mqtt import HydroColumnMQTT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HydroColumn buttons."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    async_add_entities(
        [
            HydroColumnButton(coordinator, mqtt, entry, device_id, description)
            for description in BUTTON_DESCRIPTIONS
        ]
    )


class HydroColumnButton(HydroColumnEntity):
    """HydroColumn action button."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        entry: ConfigEntry,
        device_id: str,
        description: HydroColumnButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(
            coordinator,
            device_id,
            description.name,
            description.key,
            description.icon,
        )
        self.mqtt = mqtt
        self.config_entry = entry
        self.entity_description = description
        self._last_dashboard_path: str | None = None
        self._last_registration_snippet: str | None = None

    @property
    def available(self) -> bool:
        """Return button availability."""
        if not super().available:
            return False
        if self.entity_description.key == KEY_RESET_FAULT:
            return self.coordinator.fault_active
        return True

    @property
    def state(self) -> None:
        """Buttons do not expose a state."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return dashboard export metadata for the export button."""
        if self.entity_description.key != KEY_EXPORT_DASHBOARD:
            return None
        attrs: dict[str, str] = {}
        if self._last_dashboard_path:
            attrs[ATTR_DASHBOARD_PATH] = self._last_dashboard_path
        if self._last_registration_snippet:
            attrs[ATTR_REGISTRATION_SNIPPET] = self._last_registration_snippet
        return attrs or None

    async def async_press(self) -> None:
        """Handle button press."""
        if self.entity_description.key == KEY_EXPORT_DASHBOARD:
            await self._async_export_dashboard()
            return

        if self.entity_description.key == KEY_RESET_FAULT and not self.coordinator.fault_active:
            _LOGGER.warning("Ignored reset fault button press because no fault is active")
            return

        if self.entity_description.topic_suffix is None or self.entity_description.payload is None:
            _LOGGER.warning("Button %s has no MQTT command configured", self.unique_id)
            return

        await self.mqtt.async_publish(
            self.entity_description.topic_suffix,
            self.entity_description.payload,
            qos=1,
            retain=False,
        )

    async def _async_export_dashboard(self) -> None:
        """Write a populated Lovelace dashboard YAML file for this device."""
        entity_map = _registry_entity_map(self.hass, self.config_entry.entry_id)
        dashboard_text = _build_dashboard_text(
            self.coordinator.device_id,
            self.coordinator.device_name,
            entity_map,
        )
        filename = _dashboard_filename(
            self.coordinator.device_id,
            self.coordinator.device_name,
        )
        dashboard_dir = Path(self.hass.config.path("dashboards"))
        dashboard_path = dashboard_dir / filename

        await self.hass.async_add_executor_job(
            _write_dashboard_file,
            dashboard_path,
            dashboard_text,
        )

        snippet = _dashboard_registration_block(
            self.coordinator.device_id,
            self.coordinator.device_name,
            filename,
        )
        self._last_dashboard_path = str(dashboard_path)
        self._last_registration_snippet = snippet
        self.async_write_ha_state()
        _create_dashboard_notification(
            self.hass,
            self.coordinator.device_id,
            dashboard_path,
            snippet,
        )


def _registry_entity_map(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Map stable HydroColumn unique IDs to live entity IDs."""
    registry = er.async_get(hass)
    entity_map: dict[str, str] = {}
    for registry_entry in registry.entities.values():
        if registry_entry.platform != DOMAIN:
            continue
        if registry_entry.config_entry_id != entry_id:
            continue
        if registry_entry.disabled_by is not None:
            continue
        entity_map[registry_entry.unique_id] = registry_entry.entity_id
    return entity_map


def _build_dashboard_text(
    device_id: str,
    device_name: str,
    entity_map: dict[str, str],
) -> str:
    """Build Lovelace YAML using available entity registry entries."""
    cards: list[str] = []

    for key, name, minimum, maximum, green, yellow, red in (
        (KEY_EC, "EC", 0, 3.5, 1.2, 2.3, 3.0),
        (KEY_PH, "pH", 4.5, 7.5, 5.8, 6.5, 7.1),
    ):
        entity_id = _entity_id(device_id, key, entity_map)
        if entity_id:
            cards.append(
                "\n".join(
                    [
                        "- type: gauge",
                        f"  name: {_yaml_string(name)}",
                        f"  entity: {entity_id}",
                        f"  min: {minimum}",
                        f"  max: {maximum}",
                        "  needle: true",
                        "  severity:",
                        f"    green: {green}",
                        f"    yellow: {yellow}",
                        f"    red: {red}",
                    ]
                )
            )

    trend_entities = [
        _entity_id(device_id, key, entity_map)
        for key in (KEY_EC, KEY_PH, KEY_WATER_TEMP)
    ]
    trend_entities = [entity_id for entity_id in trend_entities if entity_id]
    if trend_entities:
        lines = [
            "- type: statistic-graph",
            "  title: 24 Hour Trends",
            "  period: hour",
            "  days_to_show: 1",
            "  entities:",
        ]
        lines.extend(f"    - {entity_id}" for entity_id in trend_entities)
        cards.append("\n".join(lines))

    _append_entities_card(
        cards,
        "Reservoir",
        [
            _entity_id(device_id, KEY_WATER_LEVEL, entity_map),
            _entity_id(device_id, KEY_WATER_LEVEL_PCT, entity_map),
            _entity_id(device_id, KEY_WATER_TEMP, entity_map),
            _entity_id(device_id, KEY_AIR_TEMP, entity_map),
            _entity_id(device_id, KEY_AIR_HUMIDITY, entity_map),
            *[
                _entity_id(device_id, f"solution_remaining_{pump}", entity_map)
                for pump in SOLUTION_NAMES
            ],
        ],
    )
    _append_entities_card(
        cards,
        "Safety",
        [
            _entity_id(device_id, KEY_FLOOD, entity_map),
            _entity_id(device_id, KEY_FAULT_ACTIVE, entity_map),
            _entity_id(device_id, KEY_LOW_WATER, entity_map),
            _entity_id(device_id, KEY_EC_OUT_OF_RANGE, entity_map),
            _entity_id(device_id, KEY_PH_OUT_OF_RANGE, entity_map),
            *[
                _entity_id(device_id, f"low_solution_{pump}", entity_map)
                for pump in SOLUTION_NAMES
            ],
        ],
    )
    _append_entities_card(
        cards,
        "Status",
        [
            _entity_id(device_id, KEY_ONLINE, entity_map),
            _entity_id(device_id, KEY_DOSING_MODE_SENSOR, entity_map),
            _entity_id(device_id, KEY_LIGHT_RELAY_OUTPUT, entity_map),
            _entity_id(device_id, KEY_CIRCULATION_RELAY_OUTPUT, entity_map),
            *[
                _entity_id(device_id, f"dosing_pump_{pump}_status", entity_map)
                for pump in SOLUTION_NAMES
            ],
            _entity_id(device_id, KEY_AUTO_NUTRIENT_DOSING, entity_map),
            _entity_id(device_id, KEY_AUTO_PH_DOSING, entity_map),
        ],
    )
    _append_entities_card(
        cards,
        "Config",
        [
            _entity_id(device_id, KEY_EC_TARGET, entity_map),
            _entity_id(device_id, KEY_PH_TARGET_LOW, entity_map),
            _entity_id(device_id, KEY_PH_TARGET_HIGH, entity_map),
            _entity_id(device_id, KEY_DOSING_MODE_SELECT, entity_map),
        ],
    )

    action_cards = _build_action_cards(device_id, entity_map)
    cards.extend(action_cards)

    if not cards:
        cards.append(
            "\n".join(
                [
                    "- type: markdown",
                    "  content: >-",
                    "    HydroColumn entities are not registered yet. Reload the",
                    "    integration after MQTT retained messages arrive, then export",
                    "    the dashboard again.",
                ]
            )
        )

    title = f"HydroColumn - {device_name}"
    lines = [
        f"title: {_yaml_string(title)}",
        "views:",
        f"  - title: {_yaml_string(device_name)}",
        "    path: hydrocolumn",
        "    icon: mdi:sprout",
        "    type: masonry",
        "    cards:",
    ]
    for card in cards:
        lines.extend(f"      {line}" if line else "" for line in card.splitlines())
    return "\n".join(lines) + "\n"


def _append_entities_card(
    cards: list[str],
    title: str,
    entity_ids: list[str | None],
) -> None:
    """Append an entities card when at least one entity exists."""
    existing = [entity_id for entity_id in entity_ids if entity_id]
    if not existing:
        return
    lines = [
        "- type: entities",
        f"  title: {_yaml_string(title)}",
        "  entities:",
    ]
    lines.extend(f"    - entity: {entity_id}" for entity_id in existing)
    cards.append("\n".join(lines))


def _build_action_cards(device_id: str, entity_map: dict[str, str]) -> list[str]:
    """Build physical-action button cards with confirmations."""
    cards: list[str] = []
    reset_entity = _entity_id(device_id, KEY_RESET_FAULT, entity_map)
    if reset_entity:
        cards.append(
            _action_button_card(
                "Reset Fault",
                reset_entity,
                "Reset the latching HydroColumn fault?",
            )
        )

    for pump, name in SOLUTION_NAMES.items():
        entity_id = _entity_id(device_id, f"refill_solution_{pump}", entity_map)
        if entity_id:
            cards.append(
                _action_button_card(
                    f"Refill {name}",
                    entity_id,
                    f"Mark {name} as refilled?",
                )
            )
    return cards


def _action_button_card(name: str, entity_id: str, confirmation: str) -> str:
    """Return a Lovelace button card for a physical action."""
    return "\n".join(
        [
            "- type: button",
            f"  name: {_yaml_string(name)}",
            f"  entity: {entity_id}",
            "  tap_action:",
            "    action: call-service",
            "    service: button.press",
            "    target:",
            f"      entity_id: {entity_id}",
            "    confirmation:",
            f"      text: {_yaml_string(confirmation)}",
        ]
    )


def _entity_id(device_id: str, key: str, entity_map: dict[str, str]) -> str | None:
    """Return a live entity ID for a HydroColumn unique ID key."""
    return entity_map.get(f"{device_id}_{key}")


def _dashboard_filename(device_id: str, device_name: str) -> str:
    """Return a stable dashboard filename."""
    return f"{_slug(device_name)}_{_short_device_id(device_id)}.yaml"


def _dashboard_registration_key(device_id: str) -> str:
    """Return a stable Lovelace dashboard key."""
    return f"hydrocolumn_{_short_device_id(device_id)}"


def _dashboard_registration_block(
    device_id: str,
    device_name: str,
    filename: str,
) -> str:
    """Return the Lovelace YAML dashboard registration block."""
    key = _dashboard_registration_key(device_id)
    title = f"HydroColumn - {device_name}"
    return "\n".join(
        [
            "lovelace:",
            "  mode: storage",
            "  dashboards:",
            f"    {key}:",
            "      mode: yaml",
            f"      title: {_yaml_string(title)}",
            "      icon: mdi:sprout",
            "      show_in_sidebar: true",
            f"      filename: dashboards/{filename}",
        ]
    )


def _create_dashboard_notification(
    hass: HomeAssistant,
    device_id: str,
    dashboard_path: Path,
    snippet: str,
) -> None:
    """Show a persistent notification with the dashboard registration snippet."""
    persistent_notification = getattr(hass.components, "persistent_notification", None)
    if persistent_notification is None:
        _LOGGER.warning("Persistent notification component is unavailable")
        return
    message = (
        f"HydroColumn dashboard exported for `{device_id}`.\n\n"
        f"Generated file: `{dashboard_path}`\n\n"
        "Add or merge this block in `configuration.yaml`, then restart Home Assistant:\n\n"
        f"```yaml\n{snippet}\n```"
    )
    persistent_notification.async_create(
        hass,
        message,
        title="HydroColumn Dashboard Exported",
        notification_id=f"{DOMAIN}_{device_id}_dashboard_exported",
    )


def _write_dashboard_file(path: Path, text: str) -> None:
    """Write dashboard YAML to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _slug(value: str) -> str:
    """Return a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "hydrocolumn"


def _short_device_id(device_id: str) -> str:
    """Return the stable short suffix from a firmware device ID."""
    return device_id.rsplit("-", 1)[-1]


def _yaml_string(value: str) -> str:
    """Return a JSON-style quoted string, valid in YAML."""
    return json.dumps(value)
