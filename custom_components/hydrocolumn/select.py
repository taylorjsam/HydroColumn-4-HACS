"""Select entities for HydroColumn."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HA_ATTR_OPTIONS,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    SELECT_DESCRIPTIONS,
    HydroColumnSelectDescription,
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
    """Set up HydroColumn selects."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    entities = [
        HydroColumnSelect(coordinator, mqtt, device_id, description)
        for description in SELECT_DESCRIPTIONS
    ]
    async_add_entities(entities)

    for entity in entities:
        entry.async_on_unload(
            await mqtt.async_subscribe(entity.topic_suffix, entity.async_message_received)
        )


class HydroColumnSelect(HydroColumnMQTTEntity):
    """HydroColumn select entity."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        description: HydroColumnSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(
            coordinator,
            mqtt,
            device_id,
            description.name,
            description.key,
            description.state_topic_suffix,
            description.icon,
        )
        self.entity_description = description
        self._current_option: str | None = None
        self._parse_error = False

    @property
    def available(self) -> bool:
        """Return availability from LWT and payload parse state."""
        return super().available and not self._parse_error

    @property
    def state(self) -> str | None:
        """Return the HA state."""
        return self._current_option

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        return self._current_option

    @property
    def options(self) -> list[str]:
        """Return available dosing mode options."""
        return self.entity_description.options

    @property
    def capability_attributes(self) -> dict[str, list[str]]:
        """Return select capabilities without relying on SelectEntity."""
        return {HA_ATTR_OPTIONS: self.options}

    @property
    def state_attributes(self) -> dict[str, list[str]]:
        """Return select state attributes without relying on SelectEntity."""
        return self.capability_attributes

    async def async_select_option(self, option: str) -> None:
        """Publish a retained dosing mode config value."""
        if option not in self.options:
            _LOGGER.warning("Rejected unknown dosing mode option: %s", option)
            return
        await self.mqtt.async_publish(
            self.entity_description.command_topic_suffix,
            option,
            qos=1,
            retain=True,
        )

    def _handle_payload(self, payload: str) -> None:
        """Parse the dosing mode status payload."""
        option = payload.strip()
        if option not in self.options:
            raise ValueError(f"unknown dosing mode option: {option}")
        self._current_option = option
        self._parse_error = False

    def _set_parse_error(self) -> None:
        """Set state to None after malformed payload."""
        self._current_option = None
        self._parse_error = True
