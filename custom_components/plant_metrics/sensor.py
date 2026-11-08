"""Sensor platform for Plant & Orchard Metrics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_WEATHER_HUB
from .coordinator import PlantBlockCoordinator, WeatherHubCoordinator
from .entity import PlantMetricsBlockEntity, PlantMetricsWeatherHubEntity


@dataclass(frozen=True, kw_only=True)
class PlantMetricsHubSensorDescription(SensorEntityDescription):
    """Describe a Weather Hub sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class PlantMetricsBlockSensorDescription(SensorEntityDescription):
    """Describe a Plant / Orchard Block sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


# =============================================================================
# Site Weather Hub Sensors
# =============================================================================

HUB_SENSORS: tuple[PlantMetricsHubSensorDescription, ...] = (
    PlantMetricsHubSensorDescription(
        key="wet_bulb_temperature",
        name="Wet-Bulb Temperature",
        icon="mdi:thermometer-water",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("wet_bulb_c"),
        attr_fn=lambda d: {
            "air_temp_c": d.get("temp_c"),
            "rh_pct": d.get("rh_pct"),
            "note": "Critical temperature of wet plant tissue during radiative frost events.",
        },
    ),
    PlantMetricsHubSensorDescription(
        key="dew_point_temperature",
        name="Dew Point Temperature",
        icon="mdi:weather-fog",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("dew_point_c"),
    ),
    PlantMetricsHubSensorDescription(
        key="dew_point_depression",
        name="Dew Point Depression",
        icon="mdi:thermometer-lines",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("dew_depression_c"),
        attr_fn=lambda d: {
            "condensation_imminent": (d.get("dew_depression_c") or 99.0) <= 1.5
        },
    ),
    PlantMetricsHubSensorDescription(
        key="air_vpd",
        name="Air VPD",
        icon="mdi:water-thermometer",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("air_vpd_kpa"),
        attr_fn=lambda d: {
            "daily_peak_vpd_kpa": d.get("peak_vpd_daily_kpa"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="spray_delta_t",
        name="Spray Delta-T",
        icon="mdi:spray",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("delta_t_c"),
        attr_fn=lambda d: {
            "optimal_range_c": "2.0 - 8.0 °C",
            "spray_window_suitable": d.get("spray_window_suitable"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="spray_suitability_score",
        name="Spray Suitability Score",
        icon="mdi:sprinkler-variant",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("spray_window_score"),
        attr_fn=lambda d: {
            "suitable": d.get("spray_window_suitable"),
            "reasons": d.get("spray_window_reasons"),
            "wind_kmh": d.get("wind_kmh"),
            "gust_kmh": d.get("gust_kmh"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="ppfd",
        name="Photosynthetic Photon Flux Density (PPFD)",
        icon="mdi:white-balance-sunny",
        native_unit_of_measurement="µmol/m²/s",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("ppfd_umol"),
        attr_fn=lambda d: {
            "solar_irradiance_wm2": d.get("solar_wm2"),
            "uv_index": d.get("uv_index"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="dli_daily",
        name="Daily Light Integral (DLI)",
        icon="mdi:sun-clock",
        native_unit_of_measurement="mol/m²/d",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("dli_daily_mol"),
        attr_fn=lambda d: {
            "yesterday_dli_mol_m2_d": d.get("dli_yesterday_mol"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="et0_hourly_rate",
        name="Reference Evapotranspiration Rate (ET0)",
        icon="mdi:waves-arrow-up",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("et0_hourly_mm"),
        attr_fn=lambda d: {
            "method": "ASCE / FAO-56 Penman-Monteith Hourly",
        },
    ),
    PlantMetricsHubSensorDescription(
        key="et0_daily",
        name="Daily Reference Evapotranspiration (ET0)",
        icon="mdi:water-opacity",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("et0_daily_mm"),
        attr_fn=lambda d: {
            "yesterday_et0_mm": d.get("et0_yesterday_mm"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="virtual_leaf_wetness",
        name="Virtual Leaf Wetness",
        icon="mdi:leaf",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("virtual_leaf_wetness_pct"),
        attr_fn=lambda d: {
            "is_leaf_wet": d.get("is_leaf_wet"),
            "continuous_lwd_hours": d.get("continuous_lwd_hours"),
        },
    ),
    PlantMetricsHubSensorDescription(
        key="continuous_leaf_wetness_duration",
        name="Continuous Leaf Wetness Duration",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("continuous_lwd_hours"),
    ),
    PlantMetricsHubSensorDescription(
        key="wind_pollination_score",
        name="Wind Pollination Suitability Score",
        icon="mdi:weather-windy",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("wind_pollination_score"),
        attr_fn=lambda d: {
            "favorable": d.get("wind_pollination_favorable"),
            "advisory": d.get("wind_pollination_note"),
            "target_species": "Hazelnut, Thuja, Conifers",
        },
    ),
    PlantMetricsHubSensorDescription(
        key="bee_pollination_score",
        name="Bee & Insect Pollination Suitability Score",
        icon="mdi:bee-flower",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("bee_pollination_score"),
        attr_fn=lambda d: {
            "favorable": d.get("bee_pollination_favorable"),
            "advisory": d.get("bee_pollination_note"),
            "target_species": "Apple, Almond, Sweet Cherry, Stone & Pome Fruit",
        },
    ),
)


# =============================================================================
# Plant / Orchard Block Sensors (Multi-Species)
# =============================================================================

BLOCK_SENSORS: tuple[PlantMetricsBlockSensorDescription, ...] = (
    PlantMetricsBlockSensorDescription(
        key="chill_hours",
        name="Cumulative Chill Hours (0-7.2°C)",
        icon="mdi:snowflake-thermometer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get("chill_hours"),
        attr_fn=lambda d: {
            "species": d.get("species_label"),
            "profile": d.get("profile_name"),
            "model": "Weinberger 0-7.22°C Chill Hours",
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="utah_chill_units",
        name="Cumulative Utah Chill Units",
        icon="mdi:snowflake",
        native_unit_of_measurement="CU",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get("utah_chill_units"),
        attr_fn=lambda d: {
            "species": d.get("species_label"),
            "profile": d.get("profile_name"),
            "primary_chill_target_cu": d.get("primary_chill_target"),
            "secondary_chill_target_cu": d.get("secondary_chill_target"),
            "primary_fulfillment_pct": d.get("primary_chill_pct"),
            "secondary_fulfillment_pct": d.get("secondary_chill_pct"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="primary_chill_fulfillment",
        name="Primary Bud Chill Fulfillment",
        icon="mdi:flower",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("primary_chill_pct"),
        attr_fn=lambda d: {
            "accumulated_cu": d.get("utah_chill_units"),
            "target_cu": d.get("primary_chill_target"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="secondary_chill_fulfillment",
        name="Pollinizer / Catkin Chill Fulfillment",
        icon="mdi:flower-pollen",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("secondary_chill_pct"),
        attr_fn=lambda d: {
            "accumulated_cu": d.get("utah_chill_units"),
            "target_cu": d.get("secondary_chill_target"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="bloom_sync_status",
        name="Bloom & Pollination Sync Status",
        icon="mdi:sync-circle",
        value_fn=lambda d: d.get("bloom_sync_status"),
        attr_fn=lambda d: d.get("bloom_sync_attrs") or {},
    ),
    PlantMetricsBlockSensorDescription(
        key="pollination_suitability_score",
        name="Pollination Activity Score",
        icon="mdi:flower-pollen-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("pollination_window_score"),
        attr_fn=lambda d: {
            "pollination_type": d.get("pollination_type"),
            "favorable": d.get("pollination_window_favorable"),
            "advisory": d.get("pollination_window_note"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="seasonal_gdd",
        name="Seasonal Growing Degree Days (GDD)",
        icon="mdi:sun-thermometer",
        native_unit_of_measurement="°C·d",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("gdd_custom"),
        attr_fn=lambda d: {
            "base_temp_c": d.get("gdd_base_c"),
            "upper_temp_c": d.get("gdd_upper_c"),
            "gdd_6c_early_pests": d.get("gdd_6c"),
            "gdd_7c_mid_pests": d.get("gdd_7c"),
            "gdd_10c_late_pests": d.get("gdd_10c"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="canopy_temperature",
        name="Canopy Leaf Temperature",
        icon="mdi:leaf-maple",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("canopy_temp_c"),
        attr_fn=lambda d: {
            "source": d.get("canopy_temp_source"),
            "soil_temp_c": d.get("soil_temp_c"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="canopy_vpd",
        name="Canopy Leaf VPD",
        icon="mdi:leaf-circle",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("canopy_vpd_kpa"),
        attr_fn=lambda d: {
            "stomatal_stress_state": d.get("vpd_stress_state"),
            "optimal_species_range_kpa": d.get("vpd_optimal_range_kpa"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="stomatal_vpd_stress",
        name="Stomatal & VPD Stress Status",
        icon="mdi:alert-decagram-outline",
        value_fn=lambda d: d.get("vpd_stress_state"),
        attr_fn=lambda d: {
            "canopy_vpd_kpa": d.get("canopy_vpd_kpa"),
            "canopy_temp_c": d.get("canopy_temp_c"),
            "advisory": d.get("vpd_stress_note"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="crop_coefficient_kc",
        name="Plant Crop Coefficient (Kc)",
        icon="mdi:scale-balance",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("kc"),
        attr_fn=lambda d: {
            "species": d.get("species_label"),
            "phenology_stage": d.get("phenology_stage"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="etc_daily",
        name="Daily Crop Evapotranspiration (ETc)",
        icon="mdi:water-minus",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("etc_daily_mm"),
        attr_fn=lambda d: {
            "yesterday_etc_mm": d.get("etc_yesterday_mm"),
            "kc": d.get("kc"),
            "phenology_stage": d.get("phenology_stage"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="daily_plant_water_need",
        name="Daily Plant Water Demand",
        icon="mdi:watering-can",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("daily_plant_liters"),
        attr_fn=lambda d: {
            "canopy_area_m2": d.get("canopy_area_m2"),
            "etc_daily_mm": d.get("etc_daily_mm"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="daily_block_water_need",
        name="Daily Block Total Water Demand",
        icon="mdi:water-pump",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("daily_block_liters"),
        attr_fn=lambda d: {
            "plants_count": d.get("plants_count"),
            "daily_plant_liters": d.get("daily_plant_liters"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="water_deficit",
        name="Root-Zone Water Deficit",
        icon="mdi:layers-outline",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("water_deficit_mm"),
        attr_fn=lambda d: {
            "total_available_water_mm": d.get("taw_mm"),
            "readily_available_threshold_mm": d.get("raw_threshold_mm"),
            "depletion_pct": d.get("root_zone_depletion_pct"),
            "soil_moisture_avg_pct": d.get("soil_moisture_avg_pct"),
            "last_irrigation_ts": d.get("last_irrigation_ts"),
            "last_irrigation_mm": d.get("last_irrigation_mm"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="root_zone_depletion",
        name="Root-Zone Water Depletion",
        icon="mdi:water-percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("root_zone_depletion_pct"),
        attr_fn=lambda d: {
            "irrigation_trigger_pct": d.get("mad_pct"),
            "soil_moisture_wh51_avg_pct": d.get("soil_moisture_avg_pct"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="recommended_irrigation_plant",
        name="Recommended Irrigation Dose per Plant",
        icon="mdi:water-check",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("recommended_irrigation_liters_per_plant"),
        attr_fn=lambda d: {
            "irrigation_needed": d.get("irrigation_needed"),
            "block_total_recommended_liters": round(
                float(d.get("recommended_irrigation_liters_per_plant", 0.0))
                * int(d.get("plants_count", 1)),
                1,
            ),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="stage_frost_risk",
        name="Stage-Aware Frost Damage Risk",
        icon="mdi:snowflake-alert",
        value_fn=lambda d: d.get("frost_risk_level"),
        attr_fn=lambda d: d.get("frost_attrs") or {},
    ),
    PlantMetricsBlockSensorDescription(
        key="primary_disease_risk",
        name="Primary Blight & Scab Infection Risk",
        icon="mdi:mushroom-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("primary_disease_pct"),
        attr_fn=lambda d: {
            "target_pathogens": d.get("primary_disease_name"),
            "risk_level": d.get("primary_disease_level"),
            **(d.get("primary_disease_attrs") or {}),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="foliar_disease_risk",
        name="Foliar Mildew & Leaf/Needle Disease Risk",
        icon="mdi:blur",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("foliar_disease_pct"),
        attr_fn=lambda d: {
            "target_pathogens": d.get("foliar_disease_name"),
            "risk_level": d.get("foliar_disease_level"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="rot_desiccation_risk",
        name="Fruit Rot & Winter Desiccation Risk",
        icon="mdi:bacteria-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("rot_disease_pct"),
        attr_fn=lambda d: {
            "target_condition": d.get("rot_disease_name"),
            "risk_level": d.get("rot_disease_level"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="early_pest_status",
        name="Early-Season Mite & Bud Pest Status",
        icon="mdi:bug",
        value_fn=lambda d: d.get("early_pest_status"),
        attr_fn=lambda d: {
            "target_pest": d.get("early_pest_name"),
            "risk_score_pct": d.get("early_pest_risk_pct"),
            "gdd_6c": d.get("gdd_6c"),
            "advisory": d.get("early_pest_note"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="mid_pest_status",
        name="Mid-Season Weevil, Sawfly & Mite Status",
        icon="mdi:bug-outline",
        value_fn=lambda d: d.get("mid_pest_status"),
        attr_fn=lambda d: {
            "target_pest": d.get("mid_pest_name"),
            "risk_score_pct": d.get("mid_pest_risk_pct"),
            "gdd_7c": d.get("gdd_7c"),
            "soil_temp_c": d.get("soil_temp_c"),
            "advisory": d.get("mid_pest_note"),
        },
    ),
    PlantMetricsBlockSensorDescription(
        key="late_pest_status",
        name="Late-Season Moth, Borer & Stink Bug Status",
        icon="mdi:butterfly-outline",
        value_fn=lambda d: d.get("late_pest_status"),
        attr_fn=lambda d: {
            "target_pest": d.get("late_pest_name"),
            "risk_score_pct": d.get("late_pest_risk_pct"),
            "gdd_10c": d.get("gdd_10c"),
            "advisory": d.get("late_pest_note"),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plant & Orchard Metrics sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_WEATHER_HUB)

    if entry_type == ENTRY_TYPE_WEATHER_HUB:
        async_add_entities(
            PlantMetricsHubSensor(coordinator, desc) for desc in HUB_SENSORS
        )
    else:
        async_add_entities(
            PlantMetricsBlockSensor(coordinator, desc) for desc in BLOCK_SENSORS
        )


class PlantMetricsHubSensor(PlantMetricsWeatherHubEntity, SensorEntity):
    """Sensor for Weather Hub."""

    entity_description: PlantMetricsHubSensorDescription

    def __init__(
        self,
        coordinator: WeatherHubCoordinator,
        description: PlantMetricsHubSensorDescription,
    ) -> None:
        """Initialize Weather Hub sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)


class PlantMetricsBlockSensor(PlantMetricsBlockEntity, SensorEntity):
    """Sensor for Plant / Orchard Block."""

    entity_description: PlantMetricsBlockSensorDescription

    def __init__(
        self,
        coordinator: PlantBlockCoordinator,
        description: PlantMetricsBlockSensorDescription,
    ) -> None:
        """Initialize Plant Block sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.entity_description.attr_fn:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
