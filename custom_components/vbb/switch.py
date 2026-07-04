"""Switch entities for toggling VBB transport products."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_PRODUCTS, PRODUCT_OPTIONS

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up VBB product switches from a config entry."""
    switches = [
        VbbProductSwitch(entry, product) for product in PRODUCT_OPTIONS
    ]
    async_add_entities(switches)


class VbbProductSwitch(SwitchEntity):
    """Switch to enable or disable a transport product."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, product: str) -> None:
        self._entry = entry
        self._product = product
        self._attr_name = product.title()
        self._attr_unique_id = f"{entry.entry_id}_{product}_enabled"

    @property
    def is_on(self) -> bool:
        products: list[str] = self._entry.options.get(
            CONF_PRODUCTS, self._entry.data.get(CONF_PRODUCTS, PRODUCT_OPTIONS)
        )
        return self._product in products

    async def async_turn_on(self, **kwargs: Any) -> None:
        products = set(
            self._entry.options.get(
                CONF_PRODUCTS, self._entry.data.get(CONF_PRODUCTS, PRODUCT_OPTIONS)
            )
        )
        products.add(self._product)
        await self._update_products(list(products))

    async def async_turn_off(self, **kwargs: Any) -> None:
        products = set(
            self._entry.options.get(
                CONF_PRODUCTS, self._entry.data.get(CONF_PRODUCTS, PRODUCT_OPTIONS)
            )
        )
        products.discard(self._product)
        await self._update_products(list(products))

    async def _update_products(self, products: list[str]) -> None:
        options = dict(self._entry.options)
        options[CONF_PRODUCTS] = products
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        await self.hass.config_entries.async_reload(self._entry.entry_id)
