"""Switch entities for HydroColumn."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PAYLOAD_FALSE,
    PAYLOAD_TRUE,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    SWITCH_DESCRIPTIONS,
    HydroColumnSwitchDescription,
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
    """Set up HydroColumn switches."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
    mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]
    device_id = coordinator.device_id

    entities = [
        HydroColumnSwitch(coordinator, mqtt, device_id, description)
        for description in SWITCH_DESCRIPTIONS
    ]
    async_add_entities(entities)

    for entity in entities:
        entry.async_on_unload(
            await mqtt.async_subscribe(entity.topic_suffix, entity.async_message_received)
        )


class HydroColumnSwitch(HydroColumnMQTTEntity):
    """HydroColumn retained config switch."""

    def __init__(
        self,
        coordinator: HydroColumnCoordinator,
        mqtt: HydroColumnMQTT,
        device_id: str,
        description: HydroColumnSwitchDescription,
    ) -> None:
        """Initialize the switch."""
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
        self._pending_previous_state: bool | None = None
        self._pending_timer: asyncio.TimerHandle | None = None

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
        """Return whether the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn the switch on."""
        await self._async_publish_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the switch off."""
        await self._async_publish_state(False)

    async def _async_publish_state(self, is_on: bool) -> None:
        """Publish and optimistically update a switch state."""
        self._cancel_pending_timer()
        self._pending_previous_state = self._is_on
        self._is_on = is_on
        self._parse_error = False
        self.async_write_ha_state()

        await self.mqtt.async_publish(
            self.topic_suffix,
            PAYLOAD_TRUE if is_on else PAYLOAD_FALSE,
            qos=1,
            retain=True,
        )
        self._pending_timer = self.hass.loop.call_later(
            5,
            self._async_revert_if_no_echo,
        )

    @callback
    def _async_revert_if_no_echo(self) -> None:
        """Revert optimistic state if no retained MQTT echo arrived."""
        previous = self._pending_previous_state
        self._pending_timer = None
        self._pending_previous_state = None
        if previous is None:
            return
        _LOGGER.warning(
            "No MQTT echo received for %s within 5 seconds; reverting state",
            self.unique_id,
        )
        self._is_on = previous
        self.async_write_ha_state()

    def _handle_payload(self, payload: str) -> None:
        """Parse a retained config switch payload."""
        normalized = payload.strip().lower()
        if normalized not in {PAYLOAD_TRUE, PAYLOAD_FALSE}:
            raise ValueError("expected true or false")
        self._cancel_pending_timer()
        self._pending_previous_state = None
        self._is_on = normalized == PAYLOAD_TRUE
        self._parse_error = False

    def _set_parse_error(self) -> None:
        """Set state to None after malformed payload."""
        self._is_on = None
        self._parse_error = True

    @callback
    def _cancel_pending_timer(self) -> None:
        """Cancel a pending optimistic-update timer."""
        if self._pending_timer is not None:
            self._pending_timer.cancel()
            self._pending_timer = None

    async def async_will_remove_from_hass(self) -> None:
        """Clean up pending timers before removal."""
        self._cancel_pending_timer()
