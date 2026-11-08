"""Number platform for seeding/calibrating Chill Units and GDD in Plant & Orchard Metrics."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up Plant & Orchard Metrics calibration number entities for Plant Blocks."""
    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_PLANT_BLOCK:
        return
    coordinator: PlantBlockCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PlantMetricsChillUnitsCalibrationNumber(coordinator),
            PlantMetricsSeasonalGddCalibrationNumber(coordinator),
        ]
    )


class PlantMetricsChillUnitsCalibrationNumber(
    PlantMetricsBlockEntity, NumberEntity
):
    """Number entity to seed or calibrate accumulated Utah Chill Units."""

    _attr_name = "Utah Chill Units Calibration"
    _attr_icon = "mdi:snowflake-tune"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.0
    _attr_native_max_value = 2500.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "CU"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize calibration number."""
        super().__init__(coordinator, "calibrate_utah_chill_units")

    @property
    def native_value(self) -> float:
        """Return current Utah Chill Units."""
        return round(self.coordinator.utah_chill_units, 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set Utah Chill Units manually."""
        await self.coordinator.async_set_chill_units(value)


class PlantMetricsSeasonalGddCalibrationNumber(
    PlantMetricsBlockEntity, NumberEntity
):
    """Number entity to seed or calibrate accumulated Seasonal GDD."""

    _attr_name = "Seasonal GDD Calibration"
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.0
    _attr_native_max_value = 5000.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "°C·d"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: PlantBlockCoordinator) -> None:
        """Initialize calibration number."""
        super().__init__(coordinator, "calibrate_seasonal_gdd")

    @property
    def native_value(self) -> float:
        """Return current seasonal GDD."""
        return round(self.coordinator.gdd_custom, 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set seasonal GDD manually."""
        await self.coordinator.async_set_gdd(value)
