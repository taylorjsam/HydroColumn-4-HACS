"""Base entity helpers for HydroColumn."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HydroColumnCoordinator
from .mqtt import HydroColumnMQTT

_LOGGER = logging.getLogger(__name__)


class HydroColumnEntity(CoordinatorEntity[HydroColumnCoordinator]):
    """Base class for all HydroColumn entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        device_id: str,
        name: str,
        key: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._attr_translation_key = key
        self._attr_unique_id = f"{device_id}_{key}"
        if icon is not None:
            self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this HydroColumn unit."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.coordinator.device_name,
            manufacturer="HydroColumn",
            model="HC-4",
            sw_version=self.coordinator.build_id,
            configuration_url=f"http://{self.coordinator.device_ip}/",
        )

    @property
    def available(self) -> bool:
        """Return availability from the LWT-driven coordinator state."""
        return self.coordinator.online


class HydroColumnMQTTEntity(HydroColumnEntity):
    """Base class for entities updated by one MQTT topic."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        name: str,
        key: str,
        topic_suffix: str,
        icon: str | None = None,
    ) -> None:
        """Initialize an MQTT-backed entity."""
        super().__init__(coordinator, device_id, name, key, icon)
        self.mqtt = mqtt
        self.topic_suffix = topic_suffix

    @callback
    def async_message_received(self, message: Any) -> None:
        """Handle an MQTT message from Home Assistant."""
        payload = getattr(message, "payload", message)
        if isinstance(payload, bytes):
            payload = payload.decode()
        try:
            self._handle_payload(str(payload))
        except ValueError as err:
            _LOGGER.warning(
                "Failed to parse MQTT payload for %s on %s: %s",
                self.unique_id,
                self.topic_suffix,
                err,
            )
            self._set_parse_error()
        self.async_write_ha_state()

    def _handle_payload(self, payload: str) -> None:
        """Handle a payload for the entity."""
        raise NotImplementedError

    def _set_parse_error(self) -> None:
        """Set an entity-specific parse error state."""
        raise NotImplementedError
