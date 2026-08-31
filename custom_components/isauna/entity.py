"""Base entity for the iSauna integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IsaunaCoordinator


class IsaunaEntity(CoordinatorEntity[IsaunaCoordinator]):
    """Common base wiring entities to the shared device + coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IsaunaCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="iSauna",
            manufacturer="iSauna Home",
            model="Basic",
            configuration_url=f"http://{coordinator.device.host}/",
        )

    @property
    def data(self) -> dict:
        """Return the latest state dict from the coordinator."""
        return self.coordinator.data or {}
