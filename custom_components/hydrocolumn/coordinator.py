"""HTTP coordinator and shared runtime state for HydroColumn."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_FAULT_DESCRIPTION,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KEY_EC_TARGET,
    KEY_PH_TARGET_HIGH,
    KEY_PH_TARGET_LOW,
    PAYLOAD_OK,
)

_LOGGER = logging.getLogger(__name__)


class HydroColumnCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate slow HTTP updates and MQTT-derived safety state."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        device_ip: str,
        username: str,
        password: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.device_id = device_id
        self.device_ip = device_ip
        self.username = username
        self.password = password
        self.manual_dose_lock = asyncio.Lock()
        self.config_values: dict[str, float] = {}
        self._online = False
        self._flood_active = False
        self._fault_active = False
        self._fault_description: str | None = None
        self._device_name = device_id

    @property
    def online(self) -> bool:
        """Return whether the device is online according to LWT."""
        return self._online

    @property
    def flood_active(self) -> bool:
        """Return whether the flood/leak sensor is active."""
        return self._flood_active

    @property
    def fault_active(self) -> bool:
        """Return whether a non-flood firmware fault is active."""
        return self._fault_active

    @property
    def fault_description(self) -> str | None:
        """Return the last fault description reported by the firmware."""
        return self._fault_description

    @property
    def device_name(self) -> str:
        """Return the human-friendly device name if the firmware reported one."""
        status = self.data.get("status", {}) if self.data else {}
        if isinstance(status, dict):
            status_name = status.get("device_name")
            if isinstance(status_name, str) and status_name.strip():
                return status_name.strip()
        return self._device_name

    @property
    def build_id(self) -> str | None:
        """Return the firmware build ID from the last HTTP status snapshot."""
        status = self.data.get("status", {}) if self.data else {}
        if isinstance(status, dict):
            build_id = status.get("build_id")
            if isinstance(build_id, str) and build_id.strip():
                return build_id.strip()
        return None

    @callback
    def async_set_online(self, online: bool) -> None:
        """Set LWT-derived online state and refresh entity availability."""
        if self._online == online:
            return
        self._online = online
        self.async_update_listeners()

    @callback
    def async_set_flood_active(self, active: bool) -> None:
        """Set the shared flood safety state."""
        if self._flood_active == active:
            return
        self._flood_active = active
        self.async_update_listeners()

    @callback
    def async_set_fault_payload(self, payload: str) -> None:
        """Set the shared fault state from the status/fault payload."""
        active = payload.strip().lower() != PAYLOAD_OK
        description = payload.strip() if active else None
        if self._fault_active == active and self._fault_description == description:
            return
        self._fault_active = active
        self._fault_description = description
        self.async_update_listeners()

    @callback
    def async_set_config_value(self, key: str, value: float) -> None:
        """Store a retained config topic value for cross-entity validation."""
        if key in {KEY_EC_TARGET, KEY_PH_TARGET_LOW, KEY_PH_TARGET_HIGH}:
            self.config_values[key] = value

    def fault_attributes(self) -> dict[str, str]:
        """Return attributes describing the active firmware fault."""
        if not self._fault_description:
            return {}
        return {ATTR_FAULT_DESCRIPTION: self._fault_description}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch slow-moving HTTP data from the controller."""
        status, history = await asyncio.gather(
            self._async_fetch_json("/api/status"),
            self._async_fetch_json("/api/history"),
        )

        if isinstance(status, dict):
            device_name = status.get("device_name")
            if isinstance(device_name, str) and device_name.strip():
                self._device_name = device_name.strip()

        return {
            "status": status if isinstance(status, dict) else {},
            "history": history if isinstance(history, list) else [],
        }

    async def _async_fetch_json(self, endpoint: str) -> Any:
        """Fetch a JSON endpoint, returning an empty result on recoverable failure."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.device_ip}{endpoint}"

        try:
            async with asyncio.timeout(DEFAULT_HTTP_TIMEOUT):
                response_context = session.get(
                    url,
                    auth=aiohttp.BasicAuth(self.username, self.password),
                )
                async with response_context as response:
                    response.raise_for_status()
                    return await response.json()
        except (aiohttp.ClientResponseError, aiohttp.ClientError) as err:
            _LOGGER.warning(
                "HTTP fetch failed for %s at %s: %s",
                self.device_id,
                endpoint,
                err,
            )
        except (asyncio.TimeoutError, ValueError) as err:
            _LOGGER.warning(
                "HTTP fetch returned no usable JSON for %s at %s: %s",
                self.device_id,
                endpoint,
                err,
            )
        return {}
