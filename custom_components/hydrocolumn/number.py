"""Number entities for HydroColumn."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HA_ATTR_MAX,
    HA_ATTR_MIN,
    HA_ATTR_MODE,
    HA_ATTR_STEP,
    HA_ATTR_UNIT_OF_MEASUREMENT,
    KEY_PH_TARGET_HIGH,
    KEY_PH_TARGET_LOW,
    NUMBER_MODE_BOX,
    NUMBER_DESCRIPTIONS,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    HydroColumnNumberDescription,
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
    """Set up HydroColumn numbers."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    entities = [
        HydroColumnNumber(coordinator, mqtt, device_id, description)
        for description in NUMBER_DESCRIPTIONS
    ]
    async_add_entities(entities)

    for entity in entities:
        entry.async_on_unload(
            await mqtt.async_subscribe(entity.topic_suffix, entity.async_message_received)
        )


class HydroColumnNumber(HydroColumnMQTTEntity):
    """HydroColumn retained config number."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        description: HydroColumnNumberDescription,
    ) -> None:
        """Initialize the number entity."""
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
        self._value: float | None = None
        self._parse_error = False

    @property
    def available(self) -> bool:
        """Return availability from LWT and payload parse state."""
        return super().available and not self._parse_error

    @property
    def state(self) -> float | None:
        """Return the HA state."""
        return self._value

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        return self._value

    @property
    def native_min_value(self) -> float:
        """Return the minimum allowed value."""
        return self.entity_description.native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum allowed value."""
        return self.entity_description.native_max_value

    @property
    def native_step(self) -> float:
        """Return the value step."""
        return self.entity_description.native_step

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the value unit."""
        return self.entity_description.unit

    @property
    def unit_of_measurement(self) -> str:
        """Return the value unit."""
        return self.entity_description.unit

    @property
    def mode(self) -> str:
        """Return the preferred number UI mode."""
        return NUMBER_MODE_BOX

    @property
    def capability_attributes(self) -> dict[str, float | str]:
        """Return number capabilities without relying on NumberEntity."""
        return {
            HA_ATTR_MIN: self.native_min_value,
            HA_ATTR_MAX: self.native_max_value,
            HA_ATTR_STEP: self.native_step,
            HA_ATTR_MODE: self.mode,
        }

    @property
    def state_attributes(self) -> dict[str, float | str]:
        """Return number state attributes without relying on NumberEntity."""
        return {
            HA_ATTR_UNIT_OF_MEASUREMENT: self.native_unit_of_measurement,
            **self.capability_attributes,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Publish a retained config number value."""
        numeric_value = float(value)
        if not self._value_in_range(numeric_value):
            _LOGGER.warning(
                "Rejected %s update for %s: value outside allowed range",
                self.entity_description.key,
                self.coordinator.device_id,
            )
            return
        if not self._ph_bounds_valid(numeric_value):
            return

        await self.mqtt.async_publish(
            self.topic_suffix,
            f"{numeric_value:.1f}",
            qos=1,
            retain=True,
        )

    def _handle_payload(self, payload: str) -> None:
        """Parse a retained config number payload."""
        try:
            value = float(payload.strip())
        except ValueError as err:
            raise ValueError("expected numeric payload") from err
        if not self._value_in_range(value):
            raise ValueError("numeric payload outside allowed range")
        self._value = value
        self._parse_error = False
        self.coordinator.async_set_config_value(self.entity_description.key, value)

    def _set_parse_error(self) -> None:
        """Set state to None after malformed payload."""
        self._value = None
        self._parse_error = True

    def _value_in_range(self, value: float) -> bool:
        """Return whether a value is inside this entity's allowed range."""
        return self.native_min_value <= value <= self.native_max_value

    def _ph_bounds_valid(self, candidate: float) -> bool:
        """Validate the pH low/high relationship before publishing."""
        values = self.coordinator.config_values
        if self.entity_description.key == KEY_PH_TARGET_LOW:
            high = values.get(KEY_PH_TARGET_HIGH)
            if high is not None and candidate >= high:
                _LOGGER.warning(
                    "Rejected pH low target %.1f because it is not below pH high %.1f",
                    candidate,
                    high,
                )
                return False
        elif self.entity_description.key == KEY_PH_TARGET_HIGH:
            low = values.get(KEY_PH_TARGET_LOW)
            if low is not None and candidate <= low:
                _LOGGER.warning(
                    "Rejected pH high target %.1f because it is not above pH low %.1f",
                    candidate,
                    low,
                )
                return False
        return True
