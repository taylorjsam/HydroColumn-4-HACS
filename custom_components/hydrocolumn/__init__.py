"""HydroColumn Home Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD as HA_CONF_PASSWORD
from homeassistant.const import CONF_USERNAME as HA_CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IP,
    CONF_PASSWORD,
    CONF_TOPIC_PREFIX,
    CONF_USERNAME,
    DEFAULT_TOPIC_PREFIX_TEMPLATE,
    DOMAIN,
    PLATFORMS,
    RUNTIME_COORDINATOR,
    RUNTIME_MQTT,
    SERVICE_FIELD_DEVICE_ID,
    SERVICE_FIELD_PUMP,
    SERVICE_FIELD_SECONDS,
    SERVICE_MANUAL_DOSE,
    SOLUTION_NAMES,
    TOPIC_CONTROL_DOSE_MANUAL,
)
from .coordinator import HydroColumnCoordinator
from .mqtt import HydroColumnMQTT

_LOGGER = logging.getLogger(__name__)

MANUAL_DOSE_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_FIELD_DEVICE_ID): cv.string,
        vol.Required(SERVICE_FIELD_PUMP): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Required(SERVICE_FIELD_SECONDS): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=30),
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration-level services."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HydroColumn from a config entry."""
    data = _entry_data(entry)
    coordinator = HydroColumnCoordinator(
        hass,
        data[CONF_DEVICE_ID],
        data[CONF_DEVICE_IP],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )
    mqtt = HydroColumnMQTT(hass, data[CONF_TOPIC_PREFIX])

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        RUNTIME_COORDINATOR: coordinator,
        RUNTIME_MQTT: mqtt,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HydroColumn config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_MANUAL_DOSE)
            hass.data.pop(DOMAIN, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload an entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _entry_data(entry: ConfigEntry) -> dict[str, str]:
    """Return config entry data with options overlaid."""
    merged: dict[str, str] = {
        CONF_DEVICE_ID: entry.data[CONF_DEVICE_ID],
        CONF_DEVICE_IP: entry.data[CONF_DEVICE_IP],
        CONF_TOPIC_PREFIX: entry.data.get(
            CONF_TOPIC_PREFIX,
            DEFAULT_TOPIC_PREFIX_TEMPLATE.format(device_id=entry.data[CONF_DEVICE_ID]),
        ),
        CONF_USERNAME: entry.data.get(CONF_USERNAME)
        or entry.data.get(HA_CONF_USERNAME, ""),
        CONF_PASSWORD: entry.data.get(CONF_PASSWORD)
        or entry.data.get(HA_CONF_PASSWORD, ""),
    }
    merged.update({key: value for key, value in entry.options.items() if value})
    return merged


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services if they are not already registered."""
    if hass.services.has_service(DOMAIN, SERVICE_MANUAL_DOSE):
        return

    async def async_handle_manual_dose(call: ServiceCall) -> None:
        """Handle the manual dose service."""
        device_id = call.data[SERVICE_FIELD_DEVICE_ID]
        pump = call.data[SERVICE_FIELD_PUMP]
        seconds = call.data[SERVICE_FIELD_SECONDS]
        runtime = _runtime_for_device(hass, device_id)

        if runtime is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_device",
                translation_placeholders={SERVICE_FIELD_DEVICE_ID: device_id},
            )

        coordinator: HydroColumnCoordinator = runtime[RUNTIME_COORDINATOR]
        mqtt: HydroColumnMQTT = runtime[RUNTIME_MQTT]

        if pump not in SOLUTION_NAMES:
            raise ServiceValidationError("pump must be between 1 and 5")
        if seconds < 1 or seconds > 30:
            raise ServiceValidationError("seconds must be between 1 and 30")
        if coordinator.flood_active:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="flood_active",
                translation_placeholders={SERVICE_FIELD_DEVICE_ID: device_id},
            )
        if not coordinator.online:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_offline",
                translation_placeholders={SERVICE_FIELD_DEVICE_ID: device_id},
            )

        async with coordinator.manual_dose_lock:
            await mqtt.async_publish_json(
                TOPIC_CONTROL_DOSE_MANUAL.format(pump=pump),
                {SERVICE_FIELD_SECONDS: seconds},
                qos=1,
                retain=False,
            )
            _LOGGER.info(
                "Published manual dose command for %s pump %s for %s seconds",
                device_id,
                pump,
                seconds,
            )
            await asyncio.sleep(seconds)

    hass.services.async_register(
        DOMAIN,
        SERVICE_MANUAL_DOSE,
        async_handle_manual_dose,
        schema=MANUAL_DOSE_SCHEMA,
    )


def _runtime_for_device(
    hass: HomeAssistant,
    device_id: str,
) -> dict[str, HydroColumnCoordinator | HydroColumnMQTT] | None:
    """Return runtime data for a configured device ID."""
    for runtime in hass.data.get(DOMAIN, {}).values():
        coordinator = runtime[RUNTIME_COORDINATOR]
        if isinstance(coordinator, HydroColumnCoordinator):
            if coordinator.device_id == device_id:
                return runtime
    return None
