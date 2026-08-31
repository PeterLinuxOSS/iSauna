"""Switch platform for the iSauna integration (light / fan outputs)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IsaunaConfigEntry
from .const import SWITCH_KEYS
from .entity import IsaunaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsaunaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iSauna light and fan switches."""
    coordinator = entry.runtime_data
    async_add_entities(IsaunaSwitch(coordinator, key) for key in SWITCH_KEYS)


class IsaunaSwitch(IsaunaEntity, SwitchEntity):
    """A light or fan output encoded into the controller's write command."""

    def __init__(self, coordinator, key: str) -> None:
        """Initialise the output."""
        super().__init__(coordinator, key)
        self._attr_translation_key = key

    @property
    def is_on(self) -> bool:
        """Return True while the output is on."""
        return bool(self.data.get(self._key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the output on."""
        await self.coordinator.async_set_local(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the output off."""
        await self.coordinator.async_set_local(self._key, False)
