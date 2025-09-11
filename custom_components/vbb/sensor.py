"""Sensor platform for VBB public transport departures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from collections import defaultdict

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
from homeassistant.util import slugify

from .const import API_URL, DOMAIN, CONF_STATION_ID, DEFAULT_NAME

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
    session = async_get_clientsession(hass)
    url = API_URL.format(station=station_id)
    async with async_timeout.timeout(10):
        resp = await session.get(url)
        data = await resp.json()
    lines: set[str] = set()
    for d in data:
        line = d.get("line", {}).get("name")
        if line:
            lines.add(line)
    sensors = [
        VbbDepartureSensor(hass, station_id, name, line, idx)
        for line in lines
        for idx in (1, 2)
    ]
    async_add_entities(sensors, True)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up VBB sensor from a config entry."""
    station_id = entry.data[CONF_STATION_ID]
    name = entry.data[CONF_NAME]
    session = async_get_clientsession(hass)
    url = API_URL.format(station=station_id)
    async with async_timeout.timeout(10):
        resp = await session.get(url)
        data = await resp.json()
    lines: set[str] = set()
    for d in data:
        line = d.get("line", {}).get("name")
        if line:
            lines.add(line)
    sensors = [
        VbbDepartureSensor(hass, station_id, name, line, idx)
        for line in lines
        for idx in (1, 2)
    ]
    async_add_entities(sensors, True)


class VbbDepartureSensor(SensorEntity):
    """Representation of a VBB departure sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:train"

    def __init__(
        self,
        hass,
        station_id: str,
        station_name: str,
        line: str,
        index: int,
    ) -> None:
        self.hass = hass
        self._station_id = station_id
        self._station_name = station_name
        self._line = line
        self._index = index
        self._direction: str | None = None
        self._attr_name = f"{line}_{index}"
        self._attr_unique_id = f"vbb_{station_id}_{slugify(line)}_{index}"
        self._attr_extra_state_attributes: dict[str, Any] = {}
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
            self._direction = None
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for d in data:
            if d.get("line", {}).get("name") != self._line:
                continue
            direction = d.get("direction")
            when = d.get("plannedWhen") or d.get("when")
            if not direction or not when:
                continue
            try:
                dep_time = datetime.fromisoformat(when)
            except ValueError:
                continue
            if dep_time <= datetime.now(dep_time.tzinfo or timezone.utc):
                continue
            grouped[direction].append(d)

        directions = sorted(grouped.keys())
        if len(directions) < self._index:
            self._direction = None
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        chosen = directions[self._index - 1]
        departures = sorted(
            grouped[chosen],
            key=lambda d: d.get("plannedWhen") or d.get("when"),
        )

        first = departures[0]
        self._direction = chosen
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
            "line": self._line,
            "direction": self._direction,
            "departures": [
                {
                    "when": d.get("plannedWhen") or d.get("when"),
                }
                for d in departures
            ],
        }
