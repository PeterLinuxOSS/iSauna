"""Climate (thermostat) platform for the iSauna integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IsaunaConfigEntry
from .const import (
    DEFAULT_DURATIONS,
    DEFAULT_HEAT_MODE,
    HEAT_MODES,
    MAX_TEMP,
    MIN_TEMP,
    MODE_OFF,
    TEMP_STEP,
)
from .entity import IsaunaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsaunaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iSauna thermostat."""
    async_add_entities([IsaunaClimate(entry.runtime_data)])


class IsaunaClimate(IsaunaEntity, ClimateEntity):
    """A thermostat that combines the sauna's target temperature and mode.

    The heating type (infra / finn / steam) is exposed as a preset; switching
    the thermostat off/on maps to the controller's ``off`` mode and back.
    """

    _attr_translation_key = "thermostat"
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_preset_modes = HEAT_MODES
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator) -> None:
        """Initialise the thermostat."""
        super().__init__(coordinator, "thermostat")
        self._last_heat_mode = DEFAULT_HEAT_MODE

    @property
    def current_temperature(self) -> float | None:
        """Return the temperature measured in the cabin."""
        if self.data.get("temperaturerror"):
            return None
        return self.data.get("currentsaunatemp")

    @property
    def target_temperature(self) -> float | None:
        """Return the staged target temperature."""
        value = self.data.get("set_temperature")
        return None if value is None else float(value)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return whether a heating mode is staged."""
        return (
            HVACMode.OFF
            if self.data.get("set_mode", MODE_OFF) == MODE_OFF
            else HVACMode.HEAT
        )

    @property
    def preset_mode(self) -> str:
        """Return the staged heating type."""
        mode = self.data.get("set_mode", MODE_OFF)
        if mode in HEAT_MODES:
            self._last_heat_mode = mode
            return mode
        return self._last_heat_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return what the sauna is doing right now."""
        if self.data.get("mode", MODE_OFF) == MODE_OFF:
            return HVACAction.OFF
        current = self.data.get("currentsaunatemp")
        desired = self.data.get("desired_temperature")
        if (
            not self.data.get("temperaturerror")
            and current is not None
            and desired is not None
            and current < desired
        ):
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Stage a new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.coordinator.async_set_local("set_temperature", int(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Start the last heating type, or stop the sauna."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_local("set_mode", MODE_OFF)
        else:
            await self._async_start(self._last_heat_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Switch to another heating type and start it."""
        await self._async_start(preset_mode)

    async def async_turn_on(self) -> None:
        """Start the last used heating type."""
        await self._async_start(self._last_heat_mode)

    async def async_turn_off(self) -> None:
        """Stop the sauna."""
        await self.coordinator.async_set_local("set_mode", MODE_OFF)

    async def _async_start(self, mode: str) -> None:
        """Start a heating mode and preset its recommended run time."""
        self._last_heat_mode = mode
        await self.coordinator.async_set_local_many(
            {"set_mode": mode, "set_min": DEFAULT_DURATIONS[mode]}
        )
