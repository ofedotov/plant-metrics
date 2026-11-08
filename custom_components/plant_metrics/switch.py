"""Switch platform for Plant & Orchard Metrics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_PLANT_BLOCK
from .coordinator import PlantBlockCoordinator
from .entity import PlantMetricsBlockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plant & Orchard Metrics switch entities for Plant Blocks."""
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_PLANT_BLOCK:
        return
    coordinator: PlantBlockCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PlantMetricsAutoStageSwitch(coordinator)])


class PlantMetricsAutoStageSwitch(PlantMetricsBlockEntity, SwitchEntity):
    """Switch to enable/disable automatic GDD & Chill phenology stage progression."""

    _attr_name = "Auto Phenology Stage Progression"
    _attr_icon = "mdi:auto-mode"

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize Auto Stage switch."""
        super().__init__(coordinator, "auto_phenology_stage")

    @property
    def is_on(self) -> bool:
        """Return true if automatic phenology stage progression is enabled."""
        if not self.coordinator.data:
            return self.coordinator.auto_stage_enabled
        return bool(self.coordinator.data.get("auto_stage_enabled", True))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic stage progression."""
        await self.coordinator.async_set_auto_stage(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable automatic stage progression (manual stage lock)."""
        await self.coordinator.async_set_auto_stage(False)
