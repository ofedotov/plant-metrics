"""Button platform for Plant & Orchard Metrics."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up Plant & Orchard Metrics button entities for Plant Blocks."""
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_PLANT_BLOCK:
        return
    coordinator: PlantBlockCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PlantMetricsLogRecommendedIrrigationButton(coordinator),
            PlantMetricsResetWaterBalanceButton(coordinator),
            PlantMetricsResetSeasonalAccumulatorsButton(coordinator),
        ]
    )


class PlantMetricsLogRecommendedIrrigationButton(
    PlantMetricsBlockEntity, ButtonEntity
):
    """Button to log the currently recommended irrigation dose and reduce deficit."""

    _attr_name = "Log Recommended Irrigation"
    _attr_icon = "mdi:water-plus"

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize button."""
        super().__init__(coordinator, "log_recommended_irrigation")

    async def async_press(self) -> None:
        """Apply recommended irrigation dose."""
        rec_liters = (
            float(
                self.coordinator.data.get(
                    "recommended_irrigation_liters_per_plant", 0.0
                )
            )
            if self.coordinator.data
            else 0.0
        )
        if rec_liters > 0:
            await self.coordinator.async_log_irrigation(liters_per_tree=rec_liters)
        else:
            await self.coordinator.async_reset_water_balance()


class PlantMetricsResetWaterBalanceButton(PlantMetricsBlockEntity, ButtonEntity):
    """Button to reset root-zone water deficit to 0.0 mm (field capacity)."""

    _attr_name = "Reset Water Deficit (Field Capacity)"
    _attr_icon = "mdi:water-sync"

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize button."""
        super().__init__(coordinator, "reset_water_deficit")

    async def async_press(self) -> None:
        """Reset water deficit to zero."""
        await self.coordinator.async_reset_water_balance()


class PlantMetricsResetSeasonalAccumulatorsButton(
    PlantMetricsBlockEntity, ButtonEntity
):
    """Button to reset seasonal Chill Hours, Utah Chill Units, and GDD counters."""

    _attr_name = "Reset Seasonal Chill & GDD"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize button."""
        super().__init__(coordinator, "reset_seasonal_accumulators")

    async def async_press(self) -> None:
        """Reset seasonal accumulators."""
        await self.coordinator.async_reset_seasonal_accumulators()
