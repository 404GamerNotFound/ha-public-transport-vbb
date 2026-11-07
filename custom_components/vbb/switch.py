"""Switch entities for toggling VBB transport products."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from . import VbbConfigEntry
from .const import CONF_PRODUCTS, DEFAULT_PRODUCTS, DOMAIN, PRODUCT_OPTIONS


async def async_setup_entry(
    hass: HomeAssistant, entry: VbbConfigEntry, async_add_entities
) -> None:
    """Set up VBB product switches from a config entry."""
    async_add_entities(VbbProductSwitch(entry, product) for product in PRODUCT_OPTIONS)


class VbbProductSwitch(SwitchEntity):
    """Switch to enable or disable a transport product for a station."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, entry: VbbConfigEntry, product: str) -> None:
        self._entry = entry
        self._product = product
        self._attr_name = product.title()
        self._attr_unique_id = f"{entry.entry_id}_{product}_enabled"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.runtime_data.station.station_id)},
        )

    def _products(self) -> set[str]:
        return set(
            self._entry.options.get(
                CONF_PRODUCTS, self._entry.data.get(CONF_PRODUCTS, DEFAULT_PRODUCTS)
            )
        )

    @property
    def is_on(self) -> bool:
        return self._product in self._products()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_products(self._products() | {self._product})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_products(self._products() - {self._product})

    async def _async_set_products(self, products: set[str]) -> None:
        # The entry's update listener reloads the integration with the new
        # product filter; no explicit reload here (that would reload twice).
        ordered = [p for p in PRODUCT_OPTIONS if p in products]
        self.hass.config_entries.async_update_entry(
            self._entry, options={**self._entry.options, CONF_PRODUCTS: ordered}
        )
