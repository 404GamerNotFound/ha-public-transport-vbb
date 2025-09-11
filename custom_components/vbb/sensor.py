"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo

from .const import API_URL, DOMAIN

CONF_STATION_ID = "station_id"
DEFAULT_NAME = "VBB Departures"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the VBB sensor platform."""
    station_id = config[CONF_STATION_ID]
    name = config[CONF_NAME]
    async_add_entities([VbbDepartureSensor(hass, station_id, name)], True)


class VbbDepartureSensor(SensorEntity):
    """Representation of a VBB departure sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:train"

    def __init__(self, hass, station_id: str, name: str) -> None:
        self.hass = hass
        self._station_id = station_id
        self._attr_name = name
        self._attr_unique_id = f"vbb_{station_id}"
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._station_name = name
        self._session = async_get_clientsession(hass)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._station_id)},
            name=self._station_name,
            manufacturer="VBB",
        )

    async def async_update(self) -> None:
        """Fetch departures from the VBB API."""
        url = API_URL.format(station=self._station_id)
        async with async_timeout.timeout(10):
            resp = await self._session.get(url)
            data = await resp.json()

        if not data:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        first = data[0]
        self._station_name = first.get("stop", {}).get("name", self._station_name)
        when = first.get("plannedWhen") or first.get("when")
        if when:
            try:
                self._attr_native_value = datetime.fromisoformat(when)
            except ValueError:
                self._attr_native_value = when
        else:
            self._attr_native_value = None

        self._attr_extra_state_attributes = {
            "departures": [
                {
                    "line": d.get("line", {}).get("name"),
                    "direction": d.get("direction"),
                    "when": d.get("plannedWhen") or d.get("when"),
                }
                for d in data
            ]
        }
