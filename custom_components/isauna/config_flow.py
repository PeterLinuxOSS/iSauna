"""Config flow for the iSauna integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TCP_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_TCP_PASSWORD,
    DOMAIN,
)
from .device import IsaunaConnectionError, IsaunaDevice


class IsaunaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iSauna."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            device = IsaunaDevice(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                tcp_password=user_input[CONF_TCP_PASSWORD],
            )
            try:
                await device.async_poll()
            except IsaunaConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="iSauna", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TCP_PASSWORD, default=DEFAULT_TCP_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
