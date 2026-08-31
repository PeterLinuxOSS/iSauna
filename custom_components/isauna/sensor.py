"""Sensor platform for the iSauna integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IsaunaConfigEntry
from .const import MODES, OPTIONAL_SENSOR_KEYS, SENTINEL_ABSENT
from .entity import IsaunaEntity


@dataclass(frozen=True, kw_only=True)
class IsaunaSensorDescription(SensorEntityDescription):
    """Describes an iSauna sensor."""

    value_fn: Callable[[dict], object]
    # Optional key whose truthiness marks the reading as unavailable.
    error_key: str | None = None


SENSORS: tuple[IsaunaSensorDescription, ...] = (
    IsaunaSensorDescription(
        key="currentsaunatemp",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("currentsaunatemp"),
        error_key="temperaturerror",
    ),
    IsaunaSensorDescription(
        key="currentsteam",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("currentsteam"),
        error_key="steamerror",
    ),
    IsaunaSensorDescription(
        key="desired_temperature",
        translation_key="desired_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("desired_temperature"),
    ),
    IsaunaSensorDescription(
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=MODES,
        value_fn=lambda d: d.get("mode"),
    ),
    IsaunaSensorDescription(
        key="infra1",
        translation_key="infra1",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("infra1"),
    ),
    IsaunaSensorDescription(
        key="infra2",
        translation_key="infra2",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("infra2"),
    ),
    IsaunaSensorDescription(
        key="timer",
        translation_key="timer",
        value_fn=lambda d: d.get("timer"),
    ),
    IsaunaSensorDescription(
        key="airtimer",
        translation_key="airtimer",
        value_fn=lambda d: d.get("airtimer"),
    ),
    IsaunaSensorDescription(
        key="floorheatcurtemp",
        translation_key="floorheatcurtemp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("floorheatcurtemp"),
        error_key="floorheaterror",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsaunaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iSauna sensors."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}

    def present(key: str) -> bool:
        if key not in data:
            return False
        if key in OPTIONAL_SENSOR_KEYS:
            return data[key] != SENTINEL_ABSENT
        return True

    async_add_entities(
        IsaunaSensor(coordinator, description)
        for description in SENSORS
        if present(description.key)
    )


class IsaunaSensor(IsaunaEntity, SensorEntity):
    """A read-only value reported by the controller."""

    entity_description: IsaunaSensorDescription

    def __init__(self, coordinator, description: IsaunaSensorDescription) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return False while the controller flags this reading as faulty."""
        if not super().available:
            return False
        error_key = self.entity_description.error_key
        return not (error_key and self.data.get(error_key))

    @property
    def native_value(self):
        """Return the reading."""
        return self.entity_description.value_fn(self.data)
