"""Number platform for the iSauna integration (staged setpoints)."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IsaunaConfigEntry
from .entity import IsaunaEntity


@dataclass(frozen=True, kw_only=True)
class IsaunaNumberDescription(NumberEntityDescription):
    """Describes a staged numeric setpoint."""


NUMBERS: tuple[IsaunaNumberDescription, ...] = (
    IsaunaNumberDescription(
        key="set_temperature",
        translation_key="set_temperature",
        native_min_value=20,
        native_max_value=120,
        native_step=2,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
    ),
    IsaunaNumberDescription(
        key="set_infra1",
        translation_key="set_infra1",
        native_min_value=0,
        native_max_value=100,
        native_step=10,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
    ),
    IsaunaNumberDescription(
        key="set_infra2",
        translation_key="set_infra2",
        native_min_value=0,
        native_max_value=100,
        native_step=10,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
    ),
    IsaunaNumberDescription(
        key="set_min",
        translation_key="set_min",
        native_min_value=0,
        native_max_value=360,
        native_step=1,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsaunaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iSauna setpoint numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        IsaunaNumber(coordinator, description) for description in NUMBERS
    )


class IsaunaNumber(IsaunaEntity, NumberEntity):
    """A setpoint applied to the controller (debounced) when changed."""

    entity_description: IsaunaNumberDescription

    def __init__(self, coordinator, description: IsaunaNumberDescription) -> None:
        """Initialise the setpoint."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the staged value."""
        value = self.data.get(self._key)
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Stage a new value."""
        await self.coordinator.async_set_local(self._key, int(value))
