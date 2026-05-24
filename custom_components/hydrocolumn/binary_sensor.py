"""Binary sensor entities for HydroColumn."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BINARY_SENSOR_DESCRIPTIONS,
    DOMAIN,
    HA_ATTR_DEVICE_CLASS,
    KEY_FAULT_ACTIVE,
    KEY_FLOOD,
    KEY_ONLINE,
    LOW_SOLUTION_BINARY_SENSOR_DESCRIPTIONS,
    PAYLOAD_OK,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    HydroColumnBinarySensorDescription,
)
from .coordinator import HydroColumnCoordinator
from .entity_base import HydroColumnMQTTEntity
from .mqtt import HydroColumnMQTT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HydroColumn binary sensors."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    entities = [
        HydroColumnBinarySensor(coordinator, mqtt, device_id, description)
        for description in (
            *BINARY_SENSOR_DESCRIPTIONS,
            *LOW_SOLUTION_BINARY_SENSOR_DESCRIPTIONS,
        )
    ]
    async_add_entities(entities)

    for entity in entities:
        entry.async_on_unload(
            await mqtt.async_subscribe(entity.topic_suffix, entity.async_message_received)
        )


class HydroColumnBinarySensor(HydroColumnMQTTEntity):
    """HydroColumn MQTT binary sensor."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        description: HydroColumnBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            coordinator,
            mqtt,
            device_id,
            description.name,
            description.key,
            description.topic_suffix,
            description.icon,
        )
        self.entity_description = description
        self._is_on: bool | None = None
        self._parse_error = False

    @property
    def available(self) -> bool:
        """Return availability from LWT and payload parse state."""
        return super().available and not self._parse_error

    @property
    def state(self) -> str | None:
        """Return the HA state."""
        if self._is_on is None:
            return None
        return STATE_ON if self._is_on else STATE_OFF

    @property
    def is_on(self) -> bool | None:
        """Return whether the binary sensor is on."""
        return self._is_on

    @property
    def device_class(self) -> str | None:
        """Return the binary sensor device class."""
        return self.entity_description.device_class

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return fault details when available."""
        if self.entity_description.key == KEY_FAULT_ACTIVE:
            return self.coordinator.fault_attributes() or None
        return None

    @property
    def state_attributes(self) -> dict[str, Any] | None:
        """Return binary sensor attributes without relying on BinarySensorEntity."""
        attrs: dict[str, Any] = {}
        if self.device_class is not None:
            attrs[HA_ATTR_DEVICE_CLASS] = self.device_class
        if self.entity_description.key == KEY_FAULT_ACTIVE:
            attrs.update(self.coordinator.fault_attributes())
        return attrs or None

    def _handle_payload(self, payload: str) -> None:
        """Parse MQTT payload into an on/off state."""
        normalized = payload.strip().lower()
        if not normalized:
            raise ValueError("empty payload")

        if self.entity_description.key == KEY_FAULT_ACTIVE:
            self._is_on = normalized != PAYLOAD_OK
            self.coordinator.async_set_fault_payload(payload)
        else:
            self._is_on = normalized == self.entity_description.on_payload

        if self.entity_description.key == KEY_ONLINE:
            self.coordinator.async_set_online(bool(self._is_on))
        elif self.entity_description.key == KEY_FLOOD:
            self.coordinator.async_set_flood_active(bool(self._is_on))

        self._parse_error = False

    def _set_parse_error(self) -> None:
        """Set state to None after malformed payload."""
        self._is_on = None
        self._parse_error = True
