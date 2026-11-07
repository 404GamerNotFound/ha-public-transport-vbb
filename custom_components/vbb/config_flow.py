"""Config flow for VBB integration with station search."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_DURATION,
    CONF_PRODUCTS,
    CONF_RESULTS,
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PRODUCTS,
    DEFAULT_DURATION,
    DEFAULT_NAME,
    DEFAULT_RESULTS,
    DEFAULT_UPDATE_INTERVAL,
    PRODUCT_OPTIONS,
    DOMAIN,
    NEARBY_PATH,
    SEARCH_PATH,
)

from .api import VbbApiError, async_request_json


def _products_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[{"label": p.title(), "value": p} for p in PRODUCT_OPTIONS],
            multiple=True,
        )
    )


class VbbConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for VBB."""

    VERSION = 1

    def __init__(self) -> None:
        self._stations: list[dict[str, Any]] = []
        self._selected_station: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step where the user searches for a station."""

        errors: dict[str, str] = {}

        if user_input is not None:
            station_name = user_input.get("station_name")
            latitude = user_input.get(CONF_LATITUDE)
            longitude = user_input.get(CONF_LONGITUDE)

            try:
                if station_name:
                    self._stations = await self._search_by_name(station_name)
                elif latitude is not None and longitude is not None:
                    self._stations = await self._search_by_coordinates(
                        latitude, longitude
                    )
                else:
                    errors["base"] = "no_input"
            except VbbApiError:
                errors["base"] = "cannot_connect"

            if not errors and not self._stations:
                errors["base"] = "no_stations"

            if not errors:
                return await self.async_step_select_station()

        data_schema = vol.Schema(
            {
                vol.Optional("station_name"): cv.string,
                vol.Optional(CONF_LATITUDE): vol.Coerce(float),
                vol.Optional(CONF_LONGITUDE): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ):
        """Let the user select one of the found stations."""

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
            self._selected_station = next(
                s for s in self._stations if s["id"] == station_id
            )
            return await self.async_step_config()

        options = [
            {"label": f"{s['name']} ({s['id']})", "value": s["id"]}
            for s in self._stations
        ]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_STATION_ID): SelectSelector(
                    SelectSelectorConfig(options=options)
                )
            }
        )

        return self.async_show_form(step_id="select_station", data_schema=data_schema)

    async def async_step_config(self, user_input: dict[str, Any] | None = None):
        """Configure additional options and create the entry."""

        assert self._selected_station is not None

        if user_input is not None:
            data = {
                CONF_STATION_ID: self._selected_station["id"],
                CONF_NAME: user_input[CONF_NAME],
                CONF_DURATION: user_input[CONF_DURATION],
                CONF_RESULTS: user_input[CONF_RESULTS],
                CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
            }
            options = {CONF_PRODUCTS: user_input.get(CONF_PRODUCTS, DEFAULT_PRODUCTS)}
            await self.async_set_unique_id(self._selected_station["id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=data[CONF_NAME], data=data, options=options
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, default=self._selected_station["name"] or DEFAULT_NAME
                ): cv.string,
                vol.Optional(
                    CONF_DURATION, default=DEFAULT_DURATION
                ): vol.All(int, vol.Range(min=1)),
                vol.Optional(
                    CONF_RESULTS, default=DEFAULT_RESULTS
                ): vol.All(int, vol.Range(min=1)),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(int, vol.Range(min=1)),
                vol.Optional(
                    CONF_PRODUCTS, default=DEFAULT_PRODUCTS
                ): _products_selector(),
            }
        )

        return self.async_show_form(step_id="config", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return VbbOptionsFlow()

    async def _search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search stations by name using the VBB API."""
        session = async_get_clientsession(self.hass)
        params = {"query": name}
        data = await async_request_json(session, SEARCH_PATH, params)
        return [s for s in data if s.get("id") and s.get("name")]

    async def _search_by_coordinates(
        self, latitude: float, longitude: float
    ) -> list[dict[str, Any]]:
        """Search stations near the given coordinates."""
        session = async_get_clientsession(self.hass)
        params = {"latitude": latitude, "longitude": longitude}
        data = await async_request_json(session, NEARBY_PATH, params)
        return [s for s in data if s.get("id") and s.get("name")]


class VbbOptionsFlow(config_entries.OptionsFlow):
    """Change polling and filter settings without re-adding the station."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        entry = self.config_entry

        def current(key: str, default: Any) -> Any:
            return entry.options.get(key, entry.data.get(key, default))

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Required(
                    CONF_DURATION, default=current(CONF_DURATION, DEFAULT_DURATION)
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Required(
                    CONF_RESULTS, default=current(CONF_RESULTS, DEFAULT_RESULTS)
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Required(
                    CONF_PRODUCTS, default=current(CONF_PRODUCTS, DEFAULT_PRODUCTS)
                ): _products_selector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
