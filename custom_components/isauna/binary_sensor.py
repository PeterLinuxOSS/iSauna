"""Binary sensor platform for the iSauna integration (controller error flags)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IsaunaConfigEntry
from .const import ERROR_KEYS
from .entity import IsaunaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsaunaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iSauna binary sensors."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    async_add_entities(
        IsaunaProblem(coordinator, key) for key in ERROR_KEYS if key in data
    )


class IsaunaProblem(IsaunaEntity, BinarySensorEntity):
    """An error flag reported by the controller."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        """Initialise the error flag."""
        super().__init__(coordinator, key)
        self._attr_translation_key = key

    @property
    def is_on(self) -> bool:
        """Return True while the controller reports this fault."""
        return bool(self.data.get(self._key))
