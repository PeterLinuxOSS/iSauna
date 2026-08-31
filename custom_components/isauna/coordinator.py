"""Data update coordinator for the iSauna integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    APPLY_DEBOUNCE,
    APPLY_RETRIES,
    DATA_TEMPLATE,
    DOMAIN,
    LOGGER,
    MAX_TOLERATED_FAILURES,
    MODE_OFF,
    PENDING_SOURCE,
    READBACK_DELAY,
    SCAN_INTERVAL_ACTIVE,
    SCAN_INTERVAL_IDLE,
    WRITABLE_KEYS,
)
from .device import IsaunaConnectionError, IsaunaDevice
from .protocol import follows_controller, should_push


class IsaunaCoordinator(DataUpdateCoordinator[dict]):
    """Polls the controller and auto-applies local control changes (debounced)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: IsaunaDevice
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL_ACTIVE,
            # HA's default read-back cooldown is 10 s, which made every change
            # look like it took ten seconds to take effect.
            request_refresh_debouncer=Debouncer(
                hass, LOGGER, cooldown=READBACK_DELAY, immediate=False
            ),
        )
        self.entry = entry
        self.device = device
        self._state: dict = dict(DATA_TEMPLATE)
        self._seeded = False
        self._fail_count = 0
        # Local edits not yet accepted by the controller; they survive polls.
        self._unpushed: dict = {}
        self._apply_failures = 0
        # Coalesce rapid changes (e.g. dragging a slider) into a single send.
        self._apply_debouncer = Debouncer(
            hass,
            LOGGER,
            cooldown=APPLY_DEBOUNCE,
            immediate=False,
            function=self._async_apply,
        )

    async def _async_update_data(self) -> dict:
        try:
            new_data = await self.device.async_poll()
        except IsaunaConnectionError as err:
            self._fail_count += 1
            # Keep serving the last known good data through brief outages so the
            # entities don't flap to "unavailable" on a single refused poll.
            if self._fail_count <= MAX_TOLERATED_FAILURES and self._seeded:
                LOGGER.debug(
                    "Poll failed (%s/%s), keeping last known data: %s",
                    self._fail_count,
                    MAX_TOLERATED_FAILURES,
                    err,
                )
                return dict(self._state)
            raise UpdateFailed(str(err)) from err

        self._fail_count = 0
        if new_data is not None:
            self._state.update(new_data)
            self._sync_pending()
            # Un-sent local edits outrank what the controller currently reports.
            self._state.update(self._unpushed)
            self._seeded = True

        # Slow down polling while the sauna is off.
        self.update_interval = (
            SCAN_INTERVAL_IDLE
            if self._state.get("mode") == MODE_OFF
            else SCAN_INTERVAL_ACTIVE
        )
        return dict(self._state)

    def _sync_pending(self) -> None:
        """Mirror the controller's own values into the staged setpoints.

        Only while it runs: then it is the authority, so a session started on
        the panel shows up in HA and a stale set_min can never truncate it.
        While the sauna is off the staged values are the user's scratchpad for
        the next session and a poll must not reset them. Seeded once either way.
        """
        if not follows_controller(self._state, self._seeded):
            return
        for staged, reported in PENDING_SOURCE.items():
            if reported in self._state:
                self._state[staged] = self._state[reported]

    async def async_set_local(self, key: str, value) -> None:
        """Apply a control change locally, then schedule a debounced send."""
        await self.async_set_local_many({key: value})

    async def async_set_local_many(self, values: dict) -> None:
        """Apply several control changes locally with a single debounced send."""
        for key, value in values.items():
            if key not in WRITABLE_KEYS:
                raise ValueError(f"unknown writable key: {key}")
            self._state[key] = value
        self._unpushed.update(values)
        self.async_set_updated_data(dict(self._state))

        if not should_push(self._state, set(values)):
            LOGGER.debug("Sauna idle, staging %s without a write", sorted(values))
            return
        await self._apply_debouncer.async_call()

    async def _async_apply(self) -> None:
        """Send the full current state to the controller, then refresh."""
        try:
            await self.device.async_apply(self._state)
        except IsaunaConnectionError as err:
            self._apply_failures += 1
            if self._apply_failures <= APPLY_RETRIES:
                LOGGER.debug(
                    "Apply failed (%s/%s), retrying: %s",
                    self._apply_failures,
                    APPLY_RETRIES,
                    err,
                )
                await self._apply_debouncer.async_call()
            else:
                # Leave the change staged; the next successful write carries it.
                LOGGER.warning("Gave up applying settings to controller: %s", err)
                self._apply_failures = 0
            return

        self._apply_failures = 0
        self._unpushed.clear()
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Cancel any pending send on unload."""
        await self._apply_debouncer.async_shutdown()
        await super().async_shutdown()
