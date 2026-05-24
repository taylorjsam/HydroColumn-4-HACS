"""Config flow for HydroColumn."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_IP,
    CONF_PASSWORD,
    CONF_TOPIC_PREFIX,
    CONF_USERNAME,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_TOPIC_PREFIX_TEMPLATE,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_ID_RE = re.compile(r"^hydrocolumn-[0-9a-fA-F]{6}$")


class HydroColumnConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a HydroColumn config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = _normalize_device_id(user_input[CONF_DEVICE_ID])
            device_ip = (user_input.get(CONF_DEVICE_IP) or f"{device_id}.local").strip()
            username = (user_input.get(CONF_USERNAME) or DEFAULT_USERNAME).strip()
            password = user_input.get(CONF_PASSWORD, "")

            if not DEVICE_ID_RE.match(device_id):
                errors[CONF_DEVICE_ID] = "invalid_device_id"
            elif not _mqtt_available(self.hass):
                errors["base"] = "mqtt_unavailable"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_DEVICE_IP: device_ip,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    }
                )

                validation_error = await _async_validate_http(
                    self.hass,
                    device_ip,
                    username,
                    password,
                )
                if validation_error is None:
                    return self.async_create_entry(
                        title=device_id,
                        data={
                            CONF_DEVICE_ID: device_id,
                            CONF_DEVICE_IP: device_ip,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_TOPIC_PREFIX: DEFAULT_TOPIC_PREFIX_TEMPLATE.format(
                                device_id=device_id
                            ),
                        },
                    )
                errors["base"] = validation_error

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HydroColumnOptionsFlowHandler:
        """Create the options flow."""
        return HydroColumnOptionsFlowHandler(config_entry)


class HydroColumnOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle HydroColumn options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        current = _merged_entry_data(self.config_entry)

        if user_input is not None:
            device_ip = (user_input.get(CONF_DEVICE_IP) or current[CONF_DEVICE_IP]).strip()
            username = (user_input.get(CONF_USERNAME) or current[CONF_USERNAME]).strip()
            password = user_input.get(CONF_PASSWORD) or current[CONF_PASSWORD]

            if not _mqtt_available(self.hass):
                errors["base"] = "mqtt_unavailable"
            else:
                validation_error = await _async_validate_http(
                    self.hass,
                    device_ip,
                    username,
                    password,
                )
                if validation_error is None:
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_DEVICE_IP: device_ip,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        },
                    )
                errors["base"] = validation_error

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
            errors=errors,
        )


def _user_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    """Return the initial setup schema."""
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_ID,
                default=defaults.get(CONF_DEVICE_ID, "hydrocolumn-a1b2c3"),
            ): str,
            vol.Optional(
                CONF_DEVICE_IP,
                default=defaults.get(CONF_DEVICE_IP, ""),
            ): str,
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME),
            ): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
        }
    )


def _options_schema(current: dict[str, str]) -> vol.Schema:
    """Return the options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE_IP, default=current[CONF_DEVICE_IP]): str,
            vol.Required(CONF_USERNAME, default=current[CONF_USERNAME]): str,
            vol.Optional(CONF_PASSWORD, default=""): str,
        }
    )


def _normalize_device_id(device_id: str) -> str:
    """Normalize a firmware device ID."""
    return device_id.strip().lower()


def _merged_entry_data(entry: config_entries.ConfigEntry) -> dict[str, str]:
    """Return entry data with options overlaid."""
    data = {
        CONF_DEVICE_ID: entry.data[CONF_DEVICE_ID],
        CONF_DEVICE_IP: entry.data[CONF_DEVICE_IP],
        CONF_USERNAME: entry.data[CONF_USERNAME],
        CONF_PASSWORD: entry.data[CONF_PASSWORD],
        CONF_TOPIC_PREFIX: entry.data[CONF_TOPIC_PREFIX],
    }
    data.update({key: value for key, value in entry.options.items() if value})
    return data


def _mqtt_available(hass: HomeAssistant) -> bool:
    """Return whether HA's MQTT integration is loaded."""
    return "mqtt" in hass.config.components and bool(
        getattr(hass.components, "mqtt", None)
    )


async def _async_validate_http(
    hass: HomeAssistant,
    device_ip: str,
    username: str,
    password: str,
) -> str | None:
    """Validate the firmware HTTP API credentials and reachability."""
    session = async_get_clientsession(hass)
    url = f"http://{device_ip}/api/status"

    try:
        async with asyncio.timeout(DEFAULT_HTTP_TIMEOUT):
            response_context = session.get(
                url,
                auth=aiohttp.BasicAuth(username, password),
            )
            async with response_context as response:
                if response.status in (401, 403):
                    return "invalid_auth"
                response.raise_for_status()
                payload = await response.json()
    except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
        return "cannot_connect"
    except aiohttp.ClientResponseError as err:
        _LOGGER.warning("HydroColumn status validation failed for %s: %s", device_ip, err)
        return "cannot_connect"
    except (aiohttp.ClientError, ValueError) as err:
        _LOGGER.warning("HydroColumn status validation returned invalid data: %s", err)
        return "unknown"

    if not isinstance(payload, dict):
        return "unknown"
    return None
