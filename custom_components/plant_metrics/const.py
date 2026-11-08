"""Constants for the Plant & Orchard Metrics integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "plant_metrics"

# Entry Types
CONF_ENTRY_TYPE: Final = "entry_type"
ENTRY_TYPE_WEATHER_HUB: Final = "weather_hub"
ENTRY_TYPE_PLANT_BLOCK: Final = "plant_block"
ENTRY_TYPE_ORCHARD_BLOCK: Final = "plant_block"

# Weather Hub Configuration Keys (Ecowitt / Weather Station Entities)
CONF_SITE_NAME: Final = "site_name"
CONF_TEMP_ENTITY: Final = "temperature_entity"
CONF_HUMIDITY_ENTITY: Final = "humidity_entity"
CONF_WIND_SPEED_ENTITY: Final = "wind_speed_entity"
CONF_WIND_GUST_ENTITY: Final = "wind_gust_entity"
CONF_SOLAR_RAD_ENTITY: Final = "solar_radiation_entity"
CONF_PRESSURE_ENTITY: Final = "pressure_entity"
CONF_RAIN_RATE_ENTITY: Final = "rain_rate_entity"
CONF_RAIN_DAILY_ENTITY: Final = "rain_daily_entity"
CONF_UV_ENTITY: Final = "uv_entity"
CONF_ELEVATION: Final = "elevation"

# Plant / Orchard Block Configuration Keys
CONF_BLOCK_NAME: Final = "block_name"
CONF_WEATHER_HUB_ENTRY_ID: Final = "weather_hub_entry_id"
CONF_PLANT_PROFILE: Final = "plant_profile"
CONF_CULTIVAR: Final = "plant_profile"
CONF_PRIMARY_CHILL_TARGET: Final = "primary_chill_target"
CONF_SECONDARY_CHILL_TARGET: Final = "secondary_chill_target"
CONF_GDD_BASE_TEMP: Final = "gdd_base_temp"
CONF_GDD_UPPER_TEMP: Final = "gdd_upper_temp"
CONF_CANOPY_AREA_M2: Final = "canopy_area_m2"
CONF_PLANTS_COUNT: Final = "plants_count"
CONF_ROOT_DEPTH_MM: Final = "root_depth_mm"
CONF_AVAILABLE_WATER_CAPACITY_MM_M: Final = "available_water_capacity_mm_m"
CONF_IRRIGATION_EFFICIENCY: Final = "irrigation_efficiency"
CONF_SOIL_MOISTURE_ENTITIES: Final = "soil_moisture_entities"
CONF_SOIL_TEMP_ENTITY: Final = "soil_temp_entity"
CONF_CANOPY_TEMP_ENTITY: Final = "canopy_temp_entity"
CONF_DORMANCY_START_MONTH: Final = "dormancy_start_month"
CONF_BIOFIX_START_MONTH: Final = "biofix_start_month"

# Plant Species
SPECIES_HAZELNUT: Final = "hazelnut"
SPECIES_APPLE: Final = "apple"
SPECIES_ALMOND: Final = "almond"
SPECIES_SWEET_CHERRY: Final = "sweet_cherry"
SPECIES_THUJA: Final = "thuja"
SPECIES_GENERIC: Final = "generic"

POLLINATION_WIND: Final = "wind"
POLLINATION_INSECT: Final = "insect"

# Defaults
DEFAULT_ELEVATION: Final = 150.0
DEFAULT_GDD_BASE_TEMP: Final = 4.5
DEFAULT_GDD_UPPER_TEMP: Final = 30.0
DEFAULT_CANOPY_AREA_M2: Final = 10.0
DEFAULT_PLANTS_COUNT: Final = 100
DEFAULT_ROOT_DEPTH_MM: Final = 500.0
DEFAULT_AWC_MM_M: Final = 140.0  # Loam soil ~140 mm/m available water capacity
DEFAULT_IRRIGATION_EFFICIENCY: Final = 0.90  # Drip irrigation efficiency
DEFAULT_DORMANCY_START_MONTH: Final = 11  # November 1st
DEFAULT_BIOFIX_START_MONTH: Final = 1  # January 1st

# Universal Plant Phenology Stages
STAGE_DORMANT: Final = "dormant"
STAGE_BUD_SWELL: Final = "bud_swell"
STAGE_BLOOM: Final = "bloom"
STAGE_PETAL_FALL_LEAF_OUT: Final = "petal_fall_leaf_out"
STAGE_SHOOT_GROWTH: Final = "shoot_growth"
STAGE_FRUIT_SIZING: Final = "fruit_sizing"
STAGE_MATURATION_FILL: Final = "maturation_fill"
STAGE_PRE_HARVEST: Final = "pre_harvest"
STAGE_POST_HARVEST: Final = "post_harvest"

PHENOLOGY_STAGES: Final[list[str]] = [
    STAGE_DORMANT,
    STAGE_BUD_SWELL,
    STAGE_BLOOM,
    STAGE_PETAL_FALL_LEAF_OUT,
    STAGE_SHOOT_GROWTH,
    STAGE_FRUIT_SIZING,
    STAGE_MATURATION_FILL,
    STAGE_PRE_HARVEST,
    STAGE_POST_HARVEST,
]

# FAO-56 Crop Coefficients (Kc) by Species and Phenology Stage
KC_BY_SPECIES_AND_STAGE: Final[dict[str, dict[str, float]]] = {
    SPECIES_HAZELNUT: {
        STAGE_DORMANT: 0.20,
        STAGE_BUD_SWELL: 0.25,
        STAGE_BLOOM: 0.30,
        STAGE_PETAL_FALL_LEAF_OUT: 0.45,
        STAGE_SHOOT_GROWTH: 0.65,
        STAGE_FRUIT_SIZING: 0.85,
        STAGE_MATURATION_FILL: 0.95,
        STAGE_PRE_HARVEST: 0.65,
        STAGE_POST_HARVEST: 0.40,
    },
    SPECIES_APPLE: {
        STAGE_DORMANT: 0.20,
        STAGE_BUD_SWELL: 0.30,
        STAGE_BLOOM: 0.45,
        STAGE_PETAL_FALL_LEAF_OUT: 0.60,
        STAGE_SHOOT_GROWTH: 0.80,
        STAGE_FRUIT_SIZING: 0.95,
        STAGE_MATURATION_FILL: 1.00,
        STAGE_PRE_HARVEST: 0.80,
        STAGE_POST_HARVEST: 0.45,
    },
    SPECIES_ALMOND: {
        STAGE_DORMANT: 0.20,
        STAGE_BUD_SWELL: 0.30,
        STAGE_BLOOM: 0.40,
        STAGE_PETAL_FALL_LEAF_OUT: 0.55,
        STAGE_SHOOT_GROWTH: 0.75,
        STAGE_FRUIT_SIZING: 0.90,
        STAGE_MATURATION_FILL: 0.90,
        STAGE_PRE_HARVEST: 0.65,
        STAGE_POST_HARVEST: 0.35,
    },
    SPECIES_SWEET_CHERRY: {
        STAGE_DORMANT: 0.20,
        STAGE_BUD_SWELL: 0.35,
        STAGE_BLOOM: 0.50,
        STAGE_PETAL_FALL_LEAF_OUT: 0.65,
        STAGE_SHOOT_GROWTH: 0.85,
        STAGE_FRUIT_SIZING: 0.95,
        STAGE_MATURATION_FILL: 0.95,
        STAGE_PRE_HARVEST: 0.85,
        STAGE_POST_HARVEST: 0.50,  # Post-harvest flower bud differentiation in summer
    },
    SPECIES_THUJA: {
        STAGE_DORMANT: 0.35,
        STAGE_BUD_SWELL: 0.45,
        STAGE_BLOOM: 0.55,
        STAGE_PETAL_FALL_LEAF_OUT: 0.65,
        STAGE_SHOOT_GROWTH: 0.75,
        STAGE_FRUIT_SIZING: 0.80,
        STAGE_MATURATION_FILL: 0.75,
        STAGE_PRE_HARVEST: 0.60,
        STAGE_POST_HARVEST: 0.45,
    },
    SPECIES_GENERIC: {
        STAGE_DORMANT: 0.25,
        STAGE_BUD_SWELL: 0.35,
        STAGE_BLOOM: 0.45,
        STAGE_PETAL_FALL_LEAF_OUT: 0.55,
        STAGE_SHOOT_GROWTH: 0.75,
        STAGE_FRUIT_SIZING: 0.90,
        STAGE_MATURATION_FILL: 0.95,
        STAGE_PRE_HARVEST: 0.70,
        STAGE_POST_HARVEST: 0.40,
    },
}

# Critical Frost Damage Temperatures (Wet-Bulb / Tissue °C) by Species and Phenology Stage
# Tuple of (watch_temp_c, warning_temp_c, critical_kill_temp_c)
FROST_THRESHOLDS_BY_SPECIES_AND_STAGE: Final[
    dict[str, dict[str, tuple[float, float, float]]]
] = {
    SPECIES_HAZELNUT: {
        STAGE_DORMANT: (-12.0, -15.0, -20.0),
        STAGE_BUD_SWELL: (-4.0, -6.0, -8.0),
        STAGE_BLOOM: (-5.0, -8.0, -10.0),
        STAGE_PETAL_FALL_LEAF_OUT: (1.0, -1.0, -2.5),
        STAGE_SHOOT_GROWTH: (1.5, 0.0, -1.5),
        STAGE_FRUIT_SIZING: (2.0, 0.5, -1.0),
        STAGE_MATURATION_FILL: (2.0, 0.5, -1.0),
        STAGE_PRE_HARVEST: (1.0, -1.0, -2.5),
        STAGE_POST_HARVEST: (-5.0, -8.0, -12.0),
    },
    SPECIES_APPLE: {
        STAGE_DORMANT: (-15.0, -20.0, -25.0),
        STAGE_BUD_SWELL: (-4.0, -7.5, -11.0),
        STAGE_BLOOM: (0.5, -1.7, -3.9),
        STAGE_PETAL_FALL_LEAF_OUT: (1.5, -0.5, -2.2),
        STAGE_SHOOT_GROWTH: (1.5, 0.0, -1.7),
        STAGE_FRUIT_SIZING: (1.5, 0.0, -1.5),
        STAGE_MATURATION_FILL: (1.0, -0.5, -2.0),
        STAGE_PRE_HARVEST: (0.0, -1.5, -3.0),
        STAGE_POST_HARVEST: (-6.0, -10.0, -15.0),
    },
    SPECIES_ALMOND: {
        STAGE_DORMANT: (-8.0, -12.0, -16.0),
        STAGE_BUD_SWELL: (-1.0, -3.3, -5.6),
        STAGE_BLOOM: (1.0, -1.1, -2.8),
        STAGE_PETAL_FALL_LEAF_OUT: (2.0, 0.0, -1.1),
        STAGE_SHOOT_GROWTH: (2.0, 0.0, -1.1),
        STAGE_FRUIT_SIZING: (1.5, 0.0, -1.5),
        STAGE_MATURATION_FILL: (1.5, 0.0, -1.5),
        STAGE_PRE_HARVEST: (0.5, -1.0, -2.5),
        STAGE_POST_HARVEST: (-4.0, -7.0, -11.0),
    },
    SPECIES_SWEET_CHERRY: {
        # WSU critical temperatures for Sweet Cherry (Prunus avium)
        STAGE_DORMANT: (-12.0, -16.0, -21.0),
        STAGE_BUD_SWELL: (-2.0, -5.0, -8.5),  # Swollen bud / Green tip
        STAGE_BLOOM: (0.5, -1.7, -3.9),  # First white to full bloom (T10=-2.2, T90=-3.9)
        STAGE_PETAL_FALL_LEAF_OUT: (1.5, -0.5, -2.2),  # Shuck fall
        STAGE_SHOOT_GROWTH: (2.0, 0.0, -1.7),  # Green fruitlet
        STAGE_FRUIT_SIZING: (2.0, 0.5, -1.1),
        STAGE_MATURATION_FILL: (2.0, 0.5, -1.1),
        STAGE_PRE_HARVEST: (1.5, 0.0, -1.5),
        STAGE_POST_HARVEST: (-5.0, -9.0, -14.0),
    },
    SPECIES_THUJA: {
        STAGE_DORMANT: (-20.0, -25.0, -30.0),
        STAGE_BUD_SWELL: (-6.0, -10.0, -14.0),
        STAGE_BLOOM: (-3.0, -6.0, -9.0),
        STAGE_PETAL_FALL_LEAF_OUT: (1.0, -1.5, -3.5),
        STAGE_SHOOT_GROWTH: (1.0, -1.0, -3.0),
        STAGE_FRUIT_SIZING: (0.0, -2.0, -4.5),
        STAGE_MATURATION_FILL: (-2.0, -5.0, -8.0),
        STAGE_PRE_HARVEST: (-5.0, -9.0, -14.0),
        STAGE_POST_HARVEST: (-12.0, -18.0, -24.0),
    },
    SPECIES_GENERIC: {
        STAGE_DORMANT: (-12.0, -16.0, -20.0),
        STAGE_BUD_SWELL: (-3.0, -6.0, -9.0),
        STAGE_BLOOM: (0.5, -1.5, -3.5),
        STAGE_PETAL_FALL_LEAF_OUT: (1.5, -0.5, -2.0),
        STAGE_SHOOT_GROWTH: (1.5, 0.0, -1.5),
        STAGE_FRUIT_SIZING: (1.5, 0.0, -1.5),
        STAGE_MATURATION_FILL: (1.0, -0.5, -2.0),
        STAGE_PRE_HARVEST: (0.5, -1.0, -2.5),
        STAGE_POST_HARVEST: (-5.0, -8.0, -12.0),
    },
}

# GDD thresholds for automatic stage progression by species (once chill requirement is satisfied)
STAGE_GDD_THRESHOLDS_BY_SPECIES: Final[dict[str, dict[str, float]]] = {
    SPECIES_HAZELNUT: {
        STAGE_BUD_SWELL: 35.0,
        STAGE_BLOOM: 85.0,
        STAGE_PETAL_FALL_LEAF_OUT: 160.0,
        STAGE_SHOOT_GROWTH: 300.0,
        STAGE_FRUIT_SIZING: 650.0,
        STAGE_MATURATION_FILL: 1150.0,
        STAGE_PRE_HARVEST: 1750.0,
        STAGE_POST_HARVEST: 2150.0,
    },
    SPECIES_APPLE: {
        STAGE_BUD_SWELL: 65.0,
        STAGE_BLOOM: 165.0,
        STAGE_PETAL_FALL_LEAF_OUT: 235.0,
        STAGE_SHOOT_GROWTH: 380.0,
        STAGE_FRUIT_SIZING: 750.0,
        STAGE_MATURATION_FILL: 1250.0,
        STAGE_PRE_HARVEST: 1700.0,
        STAGE_POST_HARVEST: 2100.0,
    },
    SPECIES_ALMOND: {
        STAGE_BUD_SWELL: 40.0,
        STAGE_BLOOM: 90.0,
        STAGE_PETAL_FALL_LEAF_OUT: 155.0,
        STAGE_SHOOT_GROWTH: 320.0,
        STAGE_FRUIT_SIZING: 680.0,
        STAGE_MATURATION_FILL: 1200.0,
        STAGE_PRE_HARVEST: 1750.0,
        STAGE_POST_HARVEST: 2150.0,
    },
    SPECIES_SWEET_CHERRY: {
        STAGE_BUD_SWELL: 55.0,
        STAGE_BLOOM: 130.0,
        STAGE_PETAL_FALL_LEAF_OUT: 200.0,
        STAGE_SHOOT_GROWTH: 330.0,
        STAGE_FRUIT_SIZING: 520.0,  # Early pit hardening & rapid sizing
        STAGE_MATURATION_FILL: 720.0,  # Color break & sugar accumulation
        STAGE_PRE_HARVEST: 900.0,  # Early-summer cherry harvest
        STAGE_POST_HARVEST: 1150.0,  # Summer canopy maintenance & bud differentiation
    },
    SPECIES_THUJA: {
        STAGE_BUD_SWELL: 55.0,
        STAGE_BLOOM: 110.0,
        STAGE_PETAL_FALL_LEAF_OUT: 190.0,
        STAGE_SHOOT_GROWTH: 380.0,
        STAGE_FRUIT_SIZING: 800.0,
        STAGE_MATURATION_FILL: 1300.0,
        STAGE_PRE_HARVEST: 1750.0,
        STAGE_POST_HARVEST: 2100.0,
    },
    SPECIES_GENERIC: {
        STAGE_BUD_SWELL: 50.0,
        STAGE_BLOOM: 120.0,
        STAGE_PETAL_FALL_LEAF_OUT: 200.0,
        STAGE_SHOOT_GROWTH: 350.0,
        STAGE_FRUIT_SIZING: 720.0,
        STAGE_MATURATION_FILL: 1250.0,
        STAGE_PRE_HARVEST: 1750.0,
        STAGE_POST_HARVEST: 2150.0,
    },
}

# Services
SERVICE_LOG_IRRIGATION: Final = "log_irrigation"
SERVICE_RESET_WATER_BALANCE: Final = "reset_water_balance"
SERVICE_RESET_SEASONAL_ACCUMULATORS: Final = "reset_seasonal_accumulators"
