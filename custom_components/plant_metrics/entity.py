"""Base entity classes for Plant & Orchard Metrics."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlantBlockCoordinator, WeatherHubCoordinator


class PlantMetricsWeatherHubEntity(CoordinatorEntity[WeatherHubCoordinator]):
    """Base entity for a Site Weather Hub."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WeatherHubCoordinator, key: str) -> None:
        """Initialize the Weather Hub entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.site_name,
            manufacturer="Plant & Orchard Metrics",
            model="Microclimate Weather Analytics Hub",
            entry_type=DeviceEntryType.SERVICE,
        )


class PlantMetricsBlockEntity(CoordinatorEntity[PlantBlockCoordinator]):
    """Base entity for a Plant / Orchard Block."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PlantBlockCoordinator, key: str) -> None:
        """Initialize the Plant Block entity."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        profile = coordinator.plant_profile
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.block_name,
            manufacturer="Plant & Orchard Metrics",
            model=profile.name,
            entry_type=DeviceEntryType.SERVICE,
        )
