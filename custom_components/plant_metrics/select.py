"""Select platform for Plant Phenology Stage control."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTRY_TYPE,
    DOMAIN,
    ENTRY_TYPE_PLANT_BLOCK,
    PHENOLOGY_STAGES,
)
from .coordinator import PlantBlockCoordinator
from .entity import PlantMetricsBlockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plant & Orchard Metrics select entities for Plant Blocks."""
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_PLANT_BLOCK:
        return
    coordinator: PlantBlockCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PlantMetricsPhenologyStageSelect(coordinator)])


class PlantMetricsPhenologyStageSelect(PlantMetricsBlockEntity, SelectEntity):
    """Select entity to view or override the active Plant Phenology Stage."""

    _attr_name = "Plant Phenology Stage"
    _attr_icon = "mdi:sprout"
    _attr_options = PHENOLOGY_STAGES

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize Phenology Stage select entity."""
        super().__init__(coordinator, "phenology_stage")

    @property
    def current_option(self) -> str | None:
        """Return the current phenology stage."""
        if not self.coordinator.data:
            return self.coordinator.phenology_stage
        return self.coordinator.data.get("phenology_stage")

    async def async_select_option(self, option: str) -> None:
        """Change the selected phenology stage (disables auto-stage so manual selection sticks)."""
        await self.coordinator.async_set_auto_stage(False)
        await self.coordinator.async_set_phenology_stage(option)
