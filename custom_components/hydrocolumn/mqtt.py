"""MQTT helpers for HydroColumn."""

from __future__ import annotations

import json
from typing import Any, Callable

from homeassistant.core import HomeAssistant


class HydroColumnMQTT:
    """Small wrapper around Home Assistant's MQTT component."""

    def __init__(self, hass: HomeAssistant, topic_prefix: str) -> None:
        """Initialize the MQTT helper."""
        self.hass = hass
        self.topic_prefix = topic_prefix.rstrip("/")

    def topic(self, suffix: str) -> str:
        """Return a full MQTT topic for a firmware suffix."""
        return f"{self.topic_prefix}/{suffix.lstrip('/')}"

    async def async_subscribe(
        self,
        suffix: str,
        callback: Callable[[Any], None],
        qos: int = 0,
    ) -> Callable[[], None]:
        """Subscribe through HA's MQTT integration and return an unsubscribe callback."""
        return await self.hass.components.mqtt.async_subscribe(
            self.hass,
            self.topic(suffix),
            callback,
            qos=qos,
        )

    async def async_publish(
        self,
        suffix: str,
        payload: str,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish a string payload through HA's MQTT integration."""
        await self.hass.components.mqtt.async_publish(
            self.hass,
            self.topic(suffix),
            payload,
            qos=qos,
            retain=retain,
        )

    async def async_publish_json(
        self,
        suffix: str,
        payload: dict[str, Any],
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish a compact JSON payload through HA's MQTT integration."""
        await self.async_publish(
            suffix,
            json.dumps(payload, separators=(",", ":")),
            qos=qos,
            retain=retain,
        )
