"""Sensor entities for HydroColumn."""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_LAST_SEEN_TS,
    ATTR_PAYLOAD_UNIT,
    DOMAIN,
    HA_ATTR_DEVICE_CLASS,
    HA_ATTR_OPTIONS,
    HA_ATTR_STATE_CLASS,
    HA_ATTR_UNIT_OF_MEASUREMENT,
    PUMP_STATUS_SENSOR_DESCRIPTIONS,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    SENSOR_DESCRIPTIONS,
    SOLUTION_REMAINING_SENSOR_DESCRIPTIONS,
    HydroColumnSensorDescription,
)
from .coordinator import HydroColumnCoordinator
from .entity_base import HydroColumnMQTTEntity
from .mqtt import HydroColumnMQTT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HydroColumn sensors."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    entities = [
        HydroColumnSensor(coordinator, mqtt, device_id, description)
        for description in (
            *SENSOR_DESCRIPTIONS,
            *SOLUTION_REMAINING_SENSOR_DESCRIPTIONS,
            *PUMP_STATUS_SENSOR_DESCRIPTIONS,
        )
    ]
    async_add_entities(entities)

    for entity in entities:
        entry.async_on_unload(
            await mqtt.async_subscribe(entity.topic_suffix, entity.async_message_received)
        )


class HydroColumnSensor(HydroColumnMQTTEntity):
    """HydroColumn MQTT sensor."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        description: HydroColumnSensorDescription,
    ) -> None:
        """Initialize the sensor."""
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
        self._state: float | str | None = None
        self._extra_attrs: dict[str, Any] = {}
        self._parse_error = False

    @property
    def available(self) -> bool:
        """Return availability from LWT and payload parse state."""
        return super().available and not self._parse_error

    @property
    def state(self) -> float | str | None:
        """Return the HA state."""
        return self._state

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor native value."""
        return self._state

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self.entity_description.unit

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit of measurement."""
        return self.entity_description.unit

    @property
    def device_class(self) -> str | None:
        """Return the sensor device class."""
        return self.entity_description.device_class

    @property
    def state_class(self) -> str | None:
        """Return the sensor state class."""
        return self.entity_description.state_class

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return parsed payload metadata."""
        return self._extra_attrs or None

    @property
    def state_attributes(self) -> dict[str, Any] | None:
        """Return sensor attributes without relying on SensorEntity."""
        attrs: dict[str, Any] = {}
        if self.unit_of_measurement is not None:
            attrs[HA_ATTR_UNIT_OF_MEASUREMENT] = self.unit_of_measurement
        if self.device_class is not None:
            attrs[HA_ATTR_DEVICE_CLASS] = self.device_class
        if self.state_class is not None:
            attrs[HA_ATTR_STATE_CLASS] = self.state_class
        if self.entity_description.options is not None:
            attrs[HA_ATTR_OPTIONS] = self.entity_description.options
        attrs.update(self._extra_attrs)
        return attrs or None

    def _handle_payload(self, payload: str) -> None:
        """Parse MQTT payload into a typed sensor value."""
        payload = payload.strip()
        if not payload:
            raise ValueError("empty payload")

        value: Any
        attrs: dict[str, Any] = {}
        if payload.startswith("{"):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as err:
                raise ValueError(f"invalid JSON: {err}") from err
            if not isinstance(data, dict) or "value" not in data:
                raise ValueError("JSON payload must contain a value field")
            value = data["value"]
            if "unit" in data:
                attrs[ATTR_PAYLOAD_UNIT] = data["unit"]
            if "ts" in data:
                attrs[ATTR_LAST_SEEN_TS] = data["ts"]
        else:
            value = payload

        if self.entity_description.value_type is float:
            try:
                self._state = float(value)
            except (TypeError, ValueError) as err:
                raise ValueError(f"expected numeric value, got {value!r}") from err
        else:
            self._state = str(value)

        self._extra_attrs = attrs
        self._parse_error = False

    def _set_parse_error(self) -> None:
        """Set state to unavailable-like None after malformed payload."""
        self._state = None
        self._extra_attrs = {}
        self._parse_error = True
        _LOGGER.debug("Set %s to None after parse error", self.unique_id)
