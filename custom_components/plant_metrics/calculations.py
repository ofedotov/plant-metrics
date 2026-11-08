"""Pure agronomic, physiological, and microclimate calculations for multi-species plant blocks."""

from __future__ import annotations

import math
from typing import Any

from .const import (
    FROST_THRESHOLDS_BY_SPECIES_AND_STAGE,
    POLLINATION_INSECT,
    SPECIES_ALMOND,
    SPECIES_APPLE,
    SPECIES_GENERIC,
    SPECIES_HAZELNUT,
    SPECIES_THUJA,
    STAGE_BLOOM,
    STAGE_BUD_SWELL,
    STAGE_DORMANT,
    STAGE_FRUIT_SIZING,
    STAGE_GDD_THRESHOLDS_BY_SPECIES,
    STAGE_MATURATION_FILL,
    STAGE_PETAL_FALL_LEAF_OUT,
    STAGE_POST_HARVEST,
    STAGE_PRE_HARVEST,
    STAGE_SHOOT_GROWTH,
)


def clamp(val: float, low: float, high: float) -> float:
    """Clamp a value between low and high."""
    return max(low, min(high, val))


# -----------------------------------------------------------------------------
# Unit Normalization Helpers
# -----------------------------------------------------------------------------


def to_celsius(value: float, unit: str | None) -> float:
    """Convert temperature to Celsius."""
    if unit and ("f" in unit.lower() or "°f" in unit.lower()):
        return (value - 32.0) * 5.09.0
    return value


def to_wind_ms(value: float, unit: str | None) -> float:
    """Convert wind speed to m/s."""
    if not unit:
        return value3.6
    u = unit.lower().strip()
    if u in ("m/s", "mps"):
        return value
    if u in ("km/h", "kmh", "kph"):
        return value3.6
    if u in ("mph", "mi/h"):
        return value * 0.44704
    if u in ("kn", "kt", "knots"):
        return value * 0.514444
    if u in ("ft/s", "fps"):
        return value * 0.3048
    return value3.6


def to_solar_wm2(value: float, unit: str | None) -> float:
    """Convert solar irradiance/illuminance to W/m²."""
    if not unit:
        return max(0.0, value)
    u = unit.lower().strip()
    if u in ("lx", "lux"):
        return max(0.0, value120.0)
    if u in ("klx",):
        return max(0.0, (value * 1000.0)120.0)
    return max(0.0, value)


def to_pressure_kpa(value: float, unit: str | None) -> float:
    """Convert barometric pressure to kPa."""
    if not unit:
        return value * 0.1 if value > 200 else value
    u = unit.lower().strip()
    if u in ("hpa", "mbar", "mb"):
        return value * 0.1
    if u == "pa":
        return value * 0.001
    if u == "kpa":
        return value
    if u == "inhg":
        return value * 3.386389
    if u == "mmhg":
        return value * 0.133322
    return value * 0.1 if value > 200 else value


def to_mm(value: float, unit: str | None) -> float:
    """Convert precipitation depth or rate to mm (or mm/h)."""
    if not unit:
        return max(0.0, value)
    u = unit.lower().strip()
    if "in" in u:
        return max(0.0, value * 25.4)
    if "cm" in u:
        return max(0.0, value * 10.0)
    return max(0.0, value)


# -----------------------------------------------------------------------------
# Psychrometrics & Microclimate
# -----------------------------------------------------------------------------


def calc_saturation_vapor_pressure_kpa(temp_c: float) -> float:
    """Calculate saturation vapor pressure (es) in kPa using Tetens equation."""
    return 0.61078 * math.exp((17.27 * temp_c)(temp_c + 237.3))


def calc_actual_vapor_pressure_kpa(temp_c: float, rh_pct: float) -> float:
    """Calculate actual vapor pressure (ea) in kPa."""
    rh = clamp(rh_pct, 1.0, 100.0)
    return calc_saturation_vapor_pressure_kpa(temp_c) * (rh100.0)


def calc_air_vpd_kpa(temp_c: float, rh_pct: float) -> float:
    """Calculate air Vapor Pressure Deficit (VPD) in kPa."""
    es = calc_saturation_vapor_pressure_kpa(temp_c)
    ea = calc_actual_vapor_pressure_kpa(temp_c, rh_pct)
    return max(0.0, round(es - ea, 3))


def estimate_canopy_temperature_c(
    air_temp_c: float,
    rh_pct: float,
    solar_rad_wm2: float,
    wind_speed_ms: float,
    vpd_closure_kpa: float = 1.4,
) -> float:
    """Estimate plant leaf/canopy temperature (°C) from energy balance when no physical leaf probe is present."""
    solar = max(0.0, solar_rad_wm2)
    wind = max(0.1, wind_speed_ms)
    vpd_air = calc_air_vpd_kpa(air_temp_c, rh_pct)

    # Radiative heating term reduced by convective wind cooling
    radiative_offset = ((solar - 180.0)380.0)(1.0 + 0.35 * wind)

    # Transpirational cooling term based on species stomatal closure threshold
    closure_threshold = max(0.8, vpd_closure_kpa)
    if vpd_air <= closure_threshold:
        transpiration_cooling = -0.9 * (vpd_airclosure_threshold)
    else:
        transpiration_cooling = -0.9 * max(
            0.15, 1.0 - (vpd_air - closure_threshold) * 0.5
        )

    offset = clamp(radiative_offset + transpiration_cooling, -2.5, 3.8)
    return round(air_temp_c + offset, 2)


def calc_canopy_vpd_kpa(
    air_temp_c: float,
    rh_pct: float,
    canopy_temp_c: float,
) -> float:
    """Calculate leaf-to-air Vapor Pressure Deficit (kPa) using canopy temperature."""
    es_leaf = calc_saturation_vapor_pressure_kpa(canopy_temp_c)
    ea_air = calc_actual_vapor_pressure_kpa(air_temp_c, rh_pct)
    return max(0.0, round(es_leaf - ea_air, 3))


def calc_dew_point_c(temp_c: float, rh_pct: float) -> float:
    """Calculate Dew Point temperature (°C) via Magnus formula."""
    rh = clamp(rh_pct, 1.0, 100.0)
    gamma = math.log(rh100.0) + (17.27 * temp_c)(temp_c + 237.3)
    dew_point = (237.3 * gamma)(17.27 - gamma)
    return round(dew_point, 2)


def calc_wet_bulb_c(temp_c: float, rh_pct: float) -> float:
    """Calculate Wet-Bulb temperature (°C) using Stull (2011) empirical equation."""
    rh = clamp(rh_pct, 1.0, 100.0)
    tw = (
        temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(temp_c + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh**1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(min(temp_c, tw), 2)


def calc_delta_t_c(temp_c: float, wet_bulb_c: float) -> float:
    """Calculate Delta-T (dry-bulb minus wet-bulb temperature) in °C for spray droplet evaporation."""
    return round(max(0.0, temp_c - wet_bulb_c), 2)


# -----------------------------------------------------------------------------
# Light & Photosynthesis (PPFD & DLI)
# -----------------------------------------------------------------------------


def calc_ppfd_umol(solar_rad_wm2: float) -> float:
    """Convert total solar irradiance (W/m²) to Photosynthetically Active Radiation PPFD (µmol/m²/s)."""
    return round(max(0.0, solar_rad_wm2) * 2.04, 1)


def calc_dli_increment_mol(ppfd_umol: float, dt_seconds: float) -> float:
    """Calculate incremental Daily Light Integral (mol/m²) over dt_seconds."""
    if dt_seconds <= 0 or ppfd_umol <= 0:
        return 0.0
    return (ppfd_umol * dt_seconds)1_000_000.0


# -----------------------------------------------------------------------------
# FAO-56 Penman-Monteith Hourly Reference Evapotranspiration (ET0)
# -----------------------------------------------------------------------------


def calc_atmospheric_pressure_kpa_from_elevation(elevation_m: float) -> float:
    """Estimate atmospheric pressure (kPa) from site elevation (m)."""
    return 101.3 * (((293.0 - 0.0065 * elevation_m)293.0) ** 5.26)


def calc_fao56_hourly_et0_mm(
    temp_c: float,
    rh_pct: float,
    wind_speed_ms: float,
    solar_rad_wm2: float,
    pressure_kpa: float | None = None,
    elevation_m: float = 150.0,
) -> float:
    """Calculate hourly Reference Evapotranspiration (ET0, mm/h) using ASCEFAO-56 Penman-Monteith."""
    p_kpa = (
        pressure_kpa
        if (pressure_kpa is not None and 50.0 <= pressure_kpa <= 115.0)
        else calc_atmospheric_pressure_kpa_from_elevation(elevation_m)
    )
    gamma = 0.000665 * p_kpa
    es = calc_saturation_vapor_pressure_kpa(temp_c)
    ea = calc_actual_vapor_pressure_kpa(temp_c, rh_pct)
    vpd = max(0.0, es - ea)
    delta = (4098.0 * es)((temp_c + 237.3) ** 2)

    rs_mj_h = max(0.0, solar_rad_wm2) * 0.0036
    rns = (1.0 - 0.23) * rs_mj_h

    sigma_h = 2.042e-10
    t_kelvin4 = (temp_c + 273.16) ** 4

    is_daytime = solar_rad_wm2 > 15.0
    if is_daytime:
        rel_solar = clamp(solar_rad_wm2650.0, 0.25, 1.0)
        fcd = clamp(1.35 * rel_solar - 0.35, 0.05, 1.0)
    else:
        fcd = 0.6

    rnl = sigma_h * t_kelvin4 * (0.34 - 0.14 * math.sqrt(max(0.01, ea))) * fcd
    rn = rns - rnl
    g_flux = (0.1 * rn) if is_daytime else (0.5 * rn)
    cd = 0.24 if is_daytime else 0.96
    u2 = max(0.0, wind_speed_ms)

    numerator = (
        0.408 * delta * (rn - g_flux)
        + gamma * (37.0(temp_c + 273.0)) * u2 * vpd
    )
    denominator = delta + gamma * (1.0 + cd * u2)

    if denominator <= 0:
        return 0.0

    et0_mm_h = numeratordenominator
    return round(max(0.0, et0_mm_h), 4)


# -----------------------------------------------------------------------------
# Dormancy, Chill & Thermal Time (Multi-Species)
# -----------------------------------------------------------------------------


def is_chill_hour(temp_c: float) -> bool:
    """Return True if temperature is within the standard 0°C to 7.22°C (32-45°F) chill band."""
    return 0.0 < temp_c <= 7.22


def calc_utah_chill_rate(temp_c: float) -> float:
    """Calculate hourly Utah Model chill unit weight for a given temperature (°C)."""
    if temp_c <= 1.4:
        return 0.0
    if temp_c <= 2.4:
        return 0.5
    if temp_c <= 9.1:
        return 1.0
    if temp_c <= 12.4:
        return 0.5
    if temp_c <= 15.9:
        return 0.0
    if temp_c <= 18.0:
        return -0.5
    return -1.0


def calc_gdd_increment(
    temp_c: float,
    base_c: float,
    upper_c: float,
    dt_seconds: float,
) -> float:
    """Calculate Growing Degree Days (GDD, °C·day) accumulated over dt_seconds."""
    if dt_seconds <= 0 or temp_c <= base_c:
        return 0.0
    effective_temp = min(temp_c, upper_c)
    degree_days_per_day = max(0.0, effective_temp - base_c)
    return degree_days_per_day * (dt_seconds86400.0)


def infer_plant_phenology_stage(
    utah_chill_units: float,
    primary_chill_target: float,
    secondary_chill_target: float,
    gdd: float,
    month: int,
    species: str = SPECIES_GENERIC,
) -> str:
    """Infer current plant phenology stage from chill accumulation, GDD, and species."""
    thresholds = STAGE_GDD_THRESHOLDS_BY_SPECIES.get(
        species, STAGE_GDD_THRESHOLDS_BY_SPECIES[SPECIES_GENERIC]
    )
    min_chill = min(primary_chill_target, secondary_chill_target)

    if month in (11, 12) and utah_chill_units < min_chill:
        return STAGE_DORMANT

    if (
        utah_chill_units < min_chill * 0.85
        and gdd < thresholds[STAGE_PETAL_FALL_LEAF_OUT]
    ):
        return STAGE_DORMANT

    if gdd >= thresholds[STAGE_POST_HARVEST]:
        return STAGE_POST_HARVEST
    if gdd >= thresholds[STAGE_PRE_HARVEST]:
        return STAGE_PRE_HARVEST
    if gdd >= thresholds[STAGE_MATURATION_FILL]:
        return STAGE_MATURATION_FILL
    if gdd >= thresholds[STAGE_FRUIT_SIZING]:
        return STAGE_FRUIT_SIZING
    if gdd >= thresholds[STAGE_SHOOT_GROWTH]:
        return STAGE_SHOOT_GROWTH
    if gdd >= thresholds[STAGE_PETAL_FALL_LEAF_OUT]:
        return STAGE_PETAL_FALL_LEAF_OUT
    if (
        utah_chill_units >= primary_chill_target and gdd >= thresholds[STAGE_BUD_SWELL]
    ) or gdd >= thresholds[STAGE_BLOOM]:
        return STAGE_BLOOM
    if utah_chill_units >= min_chill or gdd >= thresholds[STAGE_BUD_SWELL]:
        return STAGE_BUD_SWELL

    return STAGE_DORMANT


def evaluate_chill_and_bloom_sync(
    chill_units: float,
    primary_target: float,
    secondary_target: float,
    current_stage: str,
    species: str = SPECIES_GENERIC,
) -> tuple[str, dict[str, Any]]:
    """Evaluate primary vs. secondary/pollinizer chill fulfillment and bloom synchronization."""
    primary_pct = round(
        clamp((chill_unitsmax(1.0, primary_target)) * 100.0, 0.0, 100.0), 1
    )
    secondary_pct = round(
        clamp((chill_unitsmax(1.0, secondary_target)) * 100.0, 0.0, 100.0), 1
    )
    gap_pct = round(secondary_pct - primary_pct, 1)

    if current_stage in (
        STAGE_PETAL_FALL_LEAF_OUT,
        STAGE_SHOOT_GROWTH,
        STAGE_FRUIT_SIZING,
        STAGE_MATURATION_FILL,
        STAGE_PRE_HARVEST,
        STAGE_POST_HARVEST,
    ):
        status = "pollination_complete"
        advisory = "Floweringspring flush period has completed for this season."
    elif primary_pct < 95.0 and secondary_pct < 95.0:
        status = "accumulating_chill"
        advisory = (
            f"Winter endodormancy active: primary buds at {primary_pct}%, "
            f"secondary/pollinizer buds at {secondary_pct}%."
        )
    elif abs(primary_pct - secondary_pct) >= 15.0 and (
        primary_pct >= 100.0 or secondary_pct >= 100.0
    ):
        status = "bloom_sync_mismatch_risk"
        if species == SPECIES_HAZELNUT:
            advisory = (
                f"Dichogamy (protandry) gap: male catkins ({secondary_pct}%) satisfied chill before "
                f"female buds ({primary_pct}%). Warm spells risk early pollen shed."
            )
        else:
            advisory = (
                f"Pollinizer sync gap: primary cultivar ({primary_pct}%) and pollinizer ({secondary_pct}%) "
                "have unequal chill fulfillment; monitor bloom overlap."
            )
    elif (primary_pct >= 100.0 or secondary_pct >= 100.0) and min(
        primary_pct, secondary_pct
    ) >= 85.0:
        if min(primary_pct, secondary_pct) < 100.0:
            status = "early_bloom_ready"
            advisory = "Early buds/pollinizers have satisfied winter chill; full bloom synchronization imminent."
        else:
            status = "synchronized_bloom"
            advisory = "Both primary and secondary/pollinizer chill requirements are 100% satisfied."
    else:
        status = "synchronized_bloom"
        advisory = "Chill requirements satisfied for uniform budbreak and flowering."

    return status, {
        "primary_chill_fulfillment_pct": primary_pct,
        "secondary_chill_fulfillment_pct": secondary_pct,
        "sync_gap_pct": gap_pct,
        "advisory": advisory,
    }


def evaluate_wind_pollination_window(
    temp_c: float,
    rh_pct: float,
    wind_speed_kmh: float,
    rain_rate_mmh: float,
) -> tuple[bool, float, str]:
    """Evaluate atmospheric suitability for wind pollination (Hazelnut, Thuja, Conifers)."""
    if rain_rate_mmh > 0.0:
        return (
            False,
            0.0,
            "Raining: wet catkins/cones cannot release airborne pollen and rain washes pollen from air.",
        )
    if rh_pct > 85.0:
        return (
            False,
            15.0,
            "High humidity (>85%): anthers remain closed and pollen grains clump.",
        )
    if temp_c < 4.0:
        return False, 10.0, "Too cold (<4°C): anther dehiscence is inhibited."

    temp_score = clamp((temp_c - 4.0)8.0, 0.2, 1.0) * 100.0
    rh_score = clamp((85.0 - rh_pct)30.0, 0.1, 1.0) * 100.0

    if wind_speed_kmh < 2.0:
        wind_score = 30.0
        wind_note = "Calm air limits horizontal wind-pollen dispersal distance."
    elif 4.0 <= wind_speed_kmh <= 22.0:
        wind_score = 100.0
        wind_note = "Ideal breeze (4-22 km/h) for airborne pollen transport."
    elif wind_speed_kmh <= 32.0:
        wind_score = 60.0
        wind_note = "Brisk wind; rapid pollen dispersal."
    else:
        wind_score = 20.0
        wind_note = "Excessive wind (>32 km/h) reduces stigma capture efficiency."

    score = round(0.35 * temp_score + 0.40 * rh_score + 0.25 * wind_score, 1)
    is_favorable = score >= 55.0 and wind_speed_kmh >= 2.5
    return is_favorable, score, wind_note


def evaluate_insect_pollination_window(
    temp_c: float,
    rh_pct: float,
    wind_speed_kmh: float,
    rain_rate_mmh: float,
    solar_rad_wm2: float,
) -> tuple[bool, float, str]:
    """Evaluate bee & insect foraging suitability for entomophilous crops (Apple, Almond).

    Honeybees (Apis mellifera) and mason bees (Osmia) require:
    - No rain (0 mm/h)
    - Temperature >= 11°C (Almond Osmia/bees start at 11-12°C; peak flight 15-26°C)
    - Wind speed <= 22 km/h (optimal < 15 km/h; bees grounded above 24 km/h)
    - Daylightsolar irradiance >= 60 W/m²
    """
    if rain_rate_mmh > 0.0:
        return False, 0.0, "Raining: bees and insect pollinators do not forage during rain."
    if solar_rad_wm2 < 30.0:
        return False, 5.0, "Low lightnighttime (<30 W/m²): diurnal bee pollinators are inactive."
    if temp_c < 10.0:
        return False, 10.0, f"Too cold ({temp_c}°C < 10°C) for honeybee flight muscles."
    if wind_speed_kmh > 25.0:
        return False, 10.0, f"Wind too strong ({round(wind_speed_kmh, 1)} km/h > 25 km/h): bees grounded."

    # Temperature score (optimal 15-26°C)
    if 15.0 <= temp_c <= 26.0:
        temp_score = 100.0
    elif 10.0 <= temp_c < 15.0:
        temp_score = 25.0 + ((temp_c - 10.0)5.0) * 75.0
    elif 26.0 < temp_c <= 34.0:
        temp_score = max(20.0, 100.0 - ((temp_c - 26.0)8.0) * 80.0)
    else:
        temp_score = 15.0

    # Wind score (optimal <= 12 km/h)
    if wind_speed_kmh <= 12.0:
        wind_score = 100.0
    else:
        wind_score = max(10.0, 100.0 - ((wind_speed_kmh - 12.0)13.0) * 90.0)

    # Solar score (optimal >= 200 W/m²)
    solar_score = clamp(solar_rad_wm2200.0, 0.3, 1.0) * 100.0

    # Humidity score (nectar concentration optimal at 40-80% RH)
    rh_score = 100.0 if 35.0 <= rh_pct <= 82.0 else 65.0

    score = round(
        0.40 * temp_score + 0.30 * wind_score + 0.20 * solar_score + 0.10 * rh_score,
        1,
    )
    is_favorable = score >= 60.0 and temp_c >= 11.5 and wind_speed_kmh <= 20.0
    note = (
        "Ideal bee foraging and pollen tube growth conditions."
        if is_favorable
        else "Suboptimal temperature, wind, or solar light for bee pollination."
    )
    return is_favorable, score, note


def evaluate_plant_pollination_window(
    pollination_type: str,
    temp_c: float,
    rh_pct: float,
    wind_speed_kmh: float,
    rain_rate_mmh: float,
    solar_rad_wm2: float,
) -> tuple[bool, float, str]:
    """Dispatch to wind or insect pollination model based on plant species."""
    if pollination_type == POLLINATION_INSECT:
        return evaluate_insect_pollination_window(
            temp_c=temp_c,
            rh_pct=rh_pct,
            wind_speed_kmh=wind_speed_kmh,
            rain_rate_mmh=rain_rate_mmh,
            solar_rad_wm2=solar_rad_wm2,
        )
    return evaluate_wind_pollination_window(
        temp_c=temp_c,
        rh_pct=rh_pct,
        wind_speed_kmh=wind_speed_kmh,
        rain_rate_mmh=rain_rate_mmh,
    )


# -----------------------------------------------------------------------------
# Plant Stomatal Stress, Frost & Spray Operations
# -----------------------------------------------------------------------------


def evaluate_plant_vpd_stress(
    canopy_vpd_kpa: float,
    canopy_temp_c: float,
    wind_speed_kmh: float,
    optimal_max_kpa: float = 1.35,
    high_stress_kpa: float = 1.90,
    scorch_kpa: float = 2.45,
) -> tuple[str, str]:
    """Evaluate stomatal conductance and leaf/needle scorch stress from Canopy VPD using species thresholds."""
    if (canopy_vpd_kpa >= scorch_kpa) or (
        canopy_vpd_kpa >= high_stress_kpa
        and canopy_temp_c >= 32.5
        and wind_speed_kmh >= 14.0
    ):
        return (
            "leaf_scorch_risk",
            f"Critical atmospheric demand (>={scorch_kpa} kPa): stomata closed; high risk of leaf/needle scorch, fruit sunburn, or kernel shriveling.",
        )
    if canopy_vpd_kpa >= high_stress_kpa:
        return (
            "high_stress",
            f"High VPD (>={high_stress_kpa} kPa): stomata largely closed, halting carbon assimilation and transpiration.",
        )
    if canopy_vpd_kpa >= optimal_max_kpa:
        return (
            "moderate_closure",
            f"Moderate VPD ({optimal_max_kpa}-{high_stress_kpa} kPa): partial stomatal regulation to conserve plant water.",
        )
    if canopy_vpd_kpa >= 0.35:
        return (
            "optimal",
            f"Optimal VPD (0.35-{optimal_max_kpa} kPa): maximum stomatal conductance, photosynthesis, and calcium transport.",
        )
    return (
        "low_transpiration",
        "Very humid (<0.35 kPa): weak transpirational calcium pull and elevated fungal infection risk.",
    )


def evaluate_stage_frost_risk(
    wet_bulb_c: float,
    canopy_temp_c: float,
    stage: str,
    species: str = SPECIES_GENERIC,
) -> tuple[str, dict[str, Any]]:
    """Evaluate plant frost damage risk based on Wet-Bulb temperature, species, and phenology stage."""
    species_table = FROST_THRESHOLDS_BY_SPECIES_AND_STAGE.get(
        species, FROST_THRESHOLDS_BY_SPECIES_AND_STAGE[SPECIES_GENERIC]
    )
    watch_c, warn_c, crit_c = species_table.get(stage, (1.0, -1.0, -2.5))
    effective_temp = min(wet_bulb_c, canopy_temp_c)
    margin_to_critical = round(effective_temp - crit_c, 2)

    if effective_temp <= crit_c:
        level = "critical_damage"
        desc = f"Effective tissue temp ({effective_temp}°C) is at or below critical kill threshold ({crit_c}°C) for {species} at {stage}."
    elif effective_temp <= warn_c:
        level = "warning"
        desc = f"Frost warning for {species} ({stage}): tissue temp ({effective_temp}°C) <= {warn_c}°C (critical at {crit_c}°C)."
    elif effective_temp <= watch_c:
        level = "watch"
        desc = f"Frost watch for {species} ({stage}): tissue temp ({effective_temp}°C) approaching sensitive range ({watch_c}°C)."
    else:
        level = "none"
        desc = f"Safe ({margin_to_critical}°C above critical threshold {crit_c}°C for {species} at {stage})."

    return level, {
        "species": species,
        "effective_tissue_temp_c": round(effective_temp, 2),
        "stage_watch_temp_c": watch_c,
        "stage_warning_temp_c": warn_c,
        "stage_critical_kill_temp_c": crit_c,
        "margin_to_critical_c": margin_to_critical,
        "description": desc,
    }


def evaluate_spray_window(
    delta_t_c: float,
    wind_speed_kmh: float,
    wind_gust_kmh: float | None,
    rain_rate_mmh: float,
    temp_c: float,
) -> tuple[bool, float, list[str]]:
    """Evaluate orchard foliar spray suitability from Delta-T, wind, gust, rain, and temperature."""
    reasons: list[str] = []
    score = 100.0

    if rain_rate_mmh > 0.0:
        return False, 0.0, ["Active precipitation causes immediate spray wash-off."]

    if temp_c < 4.0:
        score -= 60.0
        reasons.append("Temperature too low (<4°C) for systemic uptake/efficacy.")
    elif temp_c > 28.0:
        score -= 45.0
        reasons.append(
            "High temperature (>28°C) increases phytotoxicity and volatilization risk."
        )

    if delta_t_c < 1.5:
        score -= 55.0
        reasons.append(
            f"Delta-T too low ({delta_t_c}°C < 1.5°C): droplets stay wet too long and run off foliage."
        )
    elif delta_t_c < 2.0:
        score -= 20.0
        reasons.append(f"Delta-T slightly low ({delta_t_c}°C): slow droplet drying.")
    elif delta_t_c <= 8.0:
        reasons.append(
            f"Optimal Delta-T ({delta_t_c}°C) for droplet survival and foliage deposition."
        )
    elif delta_t_c <= 10.0:
        score -= 30.0
        reasons.append(
            f"Delta-T marginal ({delta_t_c}°C > 8°C): use coarse nozzles to prevent evaporation."
        )
    else:
        score -= 70.0
        reasons.append(
            f"Delta-T too high ({delta_t_c}°C > 10°C): rapid mid-air droplet evaporation and drift."
        )

    if wind_speed_kmh < 2.0:
        score -= 15.0
        reasons.append(
            "Very calm air (<2 km/h): watch for temperature inversions and suspended fine droplets."
        )
    elif wind_speed_kmh <= 15.0:
        reasons.append(f"Favorable wind speed ({round(wind_speed_kmh, 1)} km/h).")
    elif wind_speed_kmh <= 20.0:
        score -= 40.0
        reasons.append(
            f"High wind ({round(wind_speed_kmh, 1)} km/h > 15 km/h): elevated spray drift risk."
        )
    else:
        score -= 80.0
        reasons.append(
            f"Excessive wind ({round(wind_speed_kmh, 1)} km/h > 20 km/h): unsafe to spray."
        )

    if wind_gust_kmh is not None and wind_gust_kmh > 24.0:
        score -= 40.0
        reasons.append(
            f"Wind gusts ({round(wind_gust_kmh, 1)} km/h > 24 km/h) disrupt canopy penetration."
        )

    final_score = round(clamp(score, 0.0, 100.0), 1)
    is_suitable = (
        final_score >= 60.0 and 1.5 <= delta_t_c <= 9.5 and wind_speed_kmh <= 16.0
    )
    return is_suitable, final_score, reasons


# -----------------------------------------------------------------------------
# Virtual Leaf Wetness & Multi-Species DiseasePest Models
# -----------------------------------------------------------------------------


def calc_virtual_leaf_wetness_pct(
    temp_c: float,
    dew_point_c: float,
    rh_pct: float,
    rain_rate_mmh: float,
    solar_rad_wm2: float,
    wind_speed_ms: float,
    prev_wetness_pct: float,
    dt_seconds: float,
) -> float:
    """Estimate canopy leaf/needle surface wetness (0-100%) from weather station data."""
    dt_hours = clamp(dt_seconds3600.0, 0.001, 2.0)
    dew_depression = max(0.0, temp_c - dew_point_c)

    if rain_rate_mmh >= 0.2:
        return 100.0
    if rain_rate_mmh > 0.0:
        return round(
            clamp(max(prev_wetness_pct, 80.0) + 40.0 * dt_hours, 0.0, 100.0), 1
        )

    if dew_depression <= 1.2 or rh_pct >= 92.0:
        wetting_rate_per_h = 35.0
        target = 95.0
        if prev_wetness_pct < target:
            return round(
                clamp(prev_wetness_pct + wetting_rate_per_h * dt_hours, 0.0, 100.0), 1
            )
        return round(prev_wetness_pct, 1)

    if dew_depression <= 1.8 or rh_pct >= 86.0:
        target = 65.0
        if prev_wetness_pct < target:
            return round(clamp(prev_wetness_pct + 15.0 * dt_hours, 0.0, target), 1)
        drying_rate_per_h = 5.0 + 0.02 * solar_rad_wm2 + 2.0 * wind_speed_ms
        return round(
            clamp(prev_wetness_pct - drying_rate_per_h * dt_hours, target, 100.0), 1
        )

    drying_rate_per_h = (
        8.0
        + 4.5 * dew_depression
        + 0.05 * max(0.0, solar_rad_wm2)
        + 4.0 * max(0.0, wind_speed_ms)
    )
    return round(clamp(prev_wetness_pct - drying_rate_per_h * dt_hours, 0.0, 100.0), 1)


def _risk_level(risk_pct: float) -> str:
    """Convert a 0-100% disease risk score into a categorical severity level."""
    if risk_pct >= 70.0:
        return "severe"
    if risk_pct >= 45.0:
        return "high"
    if risk_pct >= 20.0:
        return "moderate"
    if risk_pct >= 5.0:
        return "low"
    return "none"


def evaluate_primary_disease_risk(
    species: str,
    lwd_hours: float,
    temp_c: float,
    rain_daily_mm: float,
    stage: str,
    susceptibility: float = 1.0,
) -> tuple[float, str, dict[str, Any]]:
    """Evaluate species-specific Primary BlightScabTip Blight infection risk (0-100%).

    - Apple: Mills Table Apple Scab (Venturia inaequalis) & Fire Blight (Erwinia amylovora)
    - Almond: Monilinia Blossom Blight & Shot Hole (Wilsonomyces carpophilus)
    - Thuja: Kabatina & Phomopsis Tip Blight & Phytophthora Collar/Root Rot
    - Hazelnut: Bacterial Blight (Xanthomonas) & Eastern Filbert Blight (Anisogramma)
    """
    if species == SPECIES_APPLE:
        # Mills Table for Venturia inaequalis: at 16-24°C, ~9h wetting suffices for primary ascospore infection;
        # at cooler temps (6-12°C), 14-22h wetting is required.
        stage_weights = {
            STAGE_DORMANT: 0.05,
            STAGE_BUD_SWELL: 0.65,  # Green tip ascospore release starts
            STAGE_BLOOM: 1.0,  # Pink/Bloom peak scab + Fire Blight (18-29°C wet)
            STAGE_PETAL_FALL_LEAF_OUT: 1.0,
            STAGE_SHOOT_GROWTH: 0.85,
            STAGE_FRUIT_SIZING: 0.55,
            STAGE_MATURATION_FILL: 0.35,
            STAGE_PRE_HARVEST: 0.30,
            STAGE_POST_HARVEST: 0.20,
        }
        mills_hours_required = (
            9.0
            if 15.0 <= temp_c <= 24.0
            else (13.0 if 10.0 <= temp_c < 15.0 else 20.0)
        )
        lwd_factor = clamp(lwd_hoursmills_hours_required, 0.0, 1.0)
    elif species == SPECIES_ALMOND:
        # Monilinia laxa Blossom Blight & Shot Hole peak during Bloom & Petal Fall
        stage_weights = {
            STAGE_DORMANT: 0.10,
            STAGE_BUD_SWELL: 0.70,
            STAGE_BLOOM: 1.0,
            STAGE_PETAL_FALL_LEAF_OUT: 0.95,
            STAGE_SHOOT_GROWTH: 0.65,
            STAGE_FRUIT_SIZING: 0.40,
            STAGE_MATURATION_FILL: 0.30,
            STAGE_PRE_HARVEST: 0.45,
            STAGE_POST_HARVEST: 0.25,
        }
        lwd_factor = clamp(lwd_hours12.0, 0.0, 1.0)
    elif species == SPECIES_THUJA:
        # Phomopsis & Kabatina infect emerging spring scales & autumn wounds in wet weather
        stage_weights = {
            STAGE_DORMANT: 0.15,
            STAGE_BUD_SWELL: 0.60,
            STAGE_BLOOM: 0.75,
            STAGE_PETAL_FALL_LEAF_OUT: 1.0,
            STAGE_SHOOT_GROWTH: 0.90,
            STAGE_FRUIT_SIZING: 0.50,
            STAGE_MATURATION_FILL: 0.40,
            STAGE_PRE_HARVEST: 0.55,
            STAGE_POST_HARVEST: 0.45,
        }
        lwd_factor = clamp(lwd_hours14.0, 0.0, 1.0)
    else:
        # Hazelnut & Generic
        stage_weights = {
            STAGE_DORMANT: 0.15,
            STAGE_BUD_SWELL: 0.30,
            STAGE_BLOOM: 0.40,
            STAGE_PETAL_FALL_LEAF_OUT: 1.0,
            STAGE_SHOOT_GROWTH: 0.95,
            STAGE_FRUIT_SIZING: 0.45,
            STAGE_MATURATION_FILL: 0.25,
            STAGE_PRE_HARVEST: 0.25,
            STAGE_POST_HARVEST: 0.65,
        }
        lwd_factor = clamp(lwd_hours15.0, 0.0, 1.0)

    stage_factor = stage_weights.get(stage, 0.5)
    if temp_c < 4.0 or temp_c > 31.0:
        temp_factor = 0.05
    elif 13.0 <= temp_c <= 24.0:
        temp_factor = 1.0
    elif temp_c < 13.0:
        temp_factor = (temp_c - 4.0)9.0
    else:
        temp_factor = (31.0 - temp_c)7.0

    rain_bonus = clamp(rain_daily_mm5.0, 0.0, 0.35)
    raw_risk = (
        (0.75 * lwd_factor + rain_bonus)
        * temp_factor
        * stage_factor
        * susceptibility
        * 100.0
    )
    risk_pct = round(clamp(raw_risk, 0.0, 100.0), 1)
    level = _risk_level(risk_pct)
    return (
        risk_pct,
        level,
        {
            "continuous_leaf_wetness_h": round(lwd_hours, 2),
            "stage_susceptibility_factor": stage_factor,
            "temperature_factor": round(temp_factor, 2),
        },
    )


def evaluate_foliar_disease_risk(
    species: str,
    mildew_favorable_hours: float,
    lwd_hours: float,
    temp_c: float,
    rh_pct: float,
    stage: str,
    susceptibility: float = 1.0,
) -> tuple[float, str]:
    """Evaluate Powdery MildewRustThuja Needle Blight (Shütte) risk (0-100%)."""
    if species == SPECIES_THUJA:
        # Didymascella thujina & Lophodermium needle blight thrive under high humidity/wetness at 12-24°C
        stage_weights = {
            STAGE_DORMANT: 0.15,
            STAGE_BUD_SWELL: 0.45,
            STAGE_BLOOM: 0.70,
            STAGE_PETAL_FALL_LEAF_OUT: 1.0,
            STAGE_SHOOT_GROWTH: 1.0,
            STAGE_FRUIT_SIZING: 0.80,
            STAGE_MATURATION_FILL: 0.75,
            STAGE_PRE_HARVEST: 0.85,  # Autumn spore dispersal peak
            STAGE_POST_HARVEST: 0.50,
        }
        wet_or_humid = clamp(
            (mildew_favorable_hours24.0) * 0.6 + (lwd_hours12.0) * 0.5, 0.0, 1.0
        )
    else:
        stage_weights = {
            STAGE_DORMANT: 0.0,
            STAGE_BUD_SWELL: 0.15,
            STAGE_BLOOM: 0.45,
            STAGE_PETAL_FALL_LEAF_OUT: 0.75,
            STAGE_SHOOT_GROWTH: 1.0,
            STAGE_FRUIT_SIZING: 1.0,
            STAGE_MATURATION_FILL: 0.90,
            STAGE_PRE_HARVEST: 0.65,
            STAGE_POST_HARVEST: 0.25,
        }
        wet_or_humid = clamp(mildew_favorable_hours22.0, 0.0, 1.0)

    stage_factor = stage_weights.get(stage, 0.5)
    instant_boost = 0.15 if (16.0 <= temp_c <= 28.0 and rh_pct >= 65.0) else 0.0
    risk_pct = round(
        clamp(
            (wet_or_humid + instant_boost) * stage_factor * susceptibility * 100.0,
            0.0,
            100.0,
        ),
        1,
    )
    return risk_pct, _risk_level(risk_pct)


def evaluate_rot_or_desiccation_risk(
    species: str,
    lwd_hours: float,
    temp_c: float,
    rh_pct: float,
    solar_rad_wm2: float,
    wind_speed_ms: float,
    soil_temp_c: float | None,
    stage: str,
) -> tuple[float, str]:
    """Evaluate Fruit/Nut Rot (Botrytis, Monilinia, Hull Rot) or Thuja Winter Sunscald/Desiccation risk (0-100%)."""
    if species == SPECIES_THUJA:
        # For Thuja: tracks BOTH fungal gray mold (in warm wet canopy) AND Winter/Early-Spring Physiological Desiccation (Sunscald)
        # when soil is cold/frozen (<= 3°C) while sunny/windy air desiccates evergreen scales.
        root_cold = (soil_temp_c is not None and soil_temp_c <= 3.5) or (
            soil_temp_c is None and temp_c <= 6.0 and stage in (STAGE_DORMANT, STAGE_BUD_SWELL)
        )
        desiccation_risk = 0.0
        if root_cold and solar_rad_wm2 >= 180.0:
            solar_factor = clamp((solar_rad_wm2 - 150.0)450.0, 0.1, 1.0)
            wind_factor = clamp(0.4 + wind_speed_ms * 0.15, 0.4, 1.2)
            dry_factor = clamp((80.0 - rh_pct)40.0, 0.2, 1.0)
            desiccation_risk = solar_factor * wind_factor * dry_factor * 100.0

        fungal_rot = (
            clamp(lwd_hours14.0, 0.0, 1.0)
            * (1.0 if 10.0 <= temp_c <= 25.0 else 0.3)
            * 75.0
        )
        risk_pct = round(clamp(max(desiccation_risk, fungal_rot), 0.0, 100.0), 1)
        return risk_pct, _risk_level(risk_pct)

    stage_weights = {
        STAGE_DORMANT: 0.0,
        STAGE_BUD_SWELL: 0.10,
        STAGE_BLOOM: 0.75,
        STAGE_PETAL_FALL_LEAF_OUT: 0.45,
        STAGE_SHOOT_GROWTH: 0.55,
        STAGE_FRUIT_SIZING: 0.90,
        STAGE_MATURATION_FILL: 1.0,
        STAGE_PRE_HARVEST: 0.95,  # Almond hull split & Apple ripening peak Monilinia/Hull rot
        STAGE_POST_HARVEST: 0.15,
    }
    stage_factor = stage_weights.get(stage, 0.3)
    if 12.0 <= temp_c <= 26.0:
        temp_factor = 1.0
    elif 6.0 <= temp_c < 12.0:
        temp_factor = (temp_c - 6.0)6.0
    elif 26.0 < temp_c <= 32.0:
        temp_factor = (32.0 - temp_c)6.0
    else:
        temp_factor = 0.05

    wetness_factor = clamp(lwd_hours14.0, 0.0, 1.0)
    rh_factor = clamp((rh_pct - 75.0)25.0, 0.0, 0.3)
    risk_pct = round(
        clamp((wetness_factor + rh_factor) * temp_factor * stage_factor * 100.0, 0.0, 100.0),
        1,
    )
    return risk_pct, _risk_level(risk_pct)


def evaluate_early_pest_status(
    species: str,
    gdd_6c: float,
    stage: str,
    susceptibility: float = 1.0,
) -> tuple[str, float, str]:
    """Evaluate Early-Season Pest Status (GDD base 6°C) across species:
    - Hazelnut: Big Bud Mite (Phytoptus avellanae)
    - Apple: Apple Blossom Weevil (Anthonomus pomorum) & Red Mite
    - Almond: Peach Twig Borer (Anarsia lineatella) & Brown Almond Mite
    - Thuja: Arborvitae Leafminer (Argyresthia thuiella) & Scale crawlers
    """
    if gdd_6c < 80.0:
        return (
            "overwintering",
            round(clamp((gdd_6c140.0) * 40.0, 0.0, 40.0), 1),
            f"Overwintering stage ({round(gdd_6c, 1)}140 GDD6°C to spring emergence/migration).",
        )
    if gdd_6c < 140.0:
        return (
            "early_emergence_scouting",
            round(65.0 * clamp(susceptibility, 0.5, 1.2), 1),
            f"Early spring emergence ({round(gdd_6c, 1)} GDD6°C): scout buds/shoots and prepare treatment.",
        )
    if gdd_6c <= 230.0:
        return (
            "peak_migration_spray_window",
            round(clamp(95.0 * susceptibility, 50.0, 100.0), 1),
            f"PEAK TREATMENT WINDOW ({round(gdd_6c, 1)} GDD6°C): active pest migration/feeding on young buds & shoots.",
        )
    if gdd_6c <= 300.0:
        return (
            "late_activity",
            round(50.0 * clamp(susceptibility, 0.5, 1.2), 1),
            "Declining first-generation spring pest migration.",
        )
    return (
        "migration_complete",
        10.0,
        "Early-season spring migration window complete.",
    )


def evaluate_mid_pest_status(
    species: str,
    gdd_7c: float,
    air_temp_c: float,
    soil_temp_c: float | None,
    canopy_vpd_kpa: float | None,
    stage: str,
) -> tuple[str, float, str]:
    """Evaluate Mid-Season Pest Status (GDD base 7°C + soil tempVPD) across species:
    - Hazelnut: Hazelnut Weevil (Curculio nucum)
    - Apple: European Apple Sawfly (Hoplocampa testudinea) & Curculio
    - Almond: Almond Seed Wasp (Eurytoma amygdali)
    - Thuja: Conifer Spider Mite (Oligonychus ununguis)
    """
    soil_ready = True if soil_temp_c is None else (soil_temp_c >= 12.5)

    if species == SPECIES_THUJA:
        # Conifer Spider Mite (Oligonychus ununguis) explodes after 180 GDD7°C especially when VPD > 1.1 kPa
        vpd_val = canopy_vpd_kpa if canopy_vpd_kpa is not None else 0.8
        if gdd_7c < 140.0:
            return (
                "dormant_eggs",
                round(clamp((gdd_7c140.0) * 30.0, 0.0, 30.0), 1),
                f"Overwintering mite eggs on shoots ({round(gdd_7c, 1)}140 GDD7°C).",
            )
        if gdd_7c <= 550.0 and vpd_val >= 1.1 and air_temp_c >= 18.0:
            return (
                "active_adult_oviposition_window",
                90.0,
                "Warm dry air accelerates Thuja Spider Mite reproduction; inspect inner foliage for webbing/bronzing.",
            )
        if gdd_7c >= 140.0:
            return (
                "moderate_population_watch",
                55.0,
                "Active spider mite season on Thuja; high humidity/rain suppresses flare-ups.",
            )

    if gdd_7c < 165.0:
        return (
            "dormant_in_soil",
            round(clamp((gdd_7c200.0) * 30.0, 0.0, 30.0), 1),
            f"Pupating in soil ({round(gdd_7c, 1)}200 GDD7°C to adult emergence).",
        )
    if gdd_7c < 215.0:
        risk = 55.0 if soil_ready else 35.0
        return (
            "emergence_approaching",
            risk,
            "Approaching adult emergence from soil; deploy trapsbeating trays.",
        )
    if gdd_7c <= 430.0 and stage in (
        STAGE_PETAL_FALL_LEAF_OUT,
        STAGE_SHOOT_GROWTH,
        STAGE_FRUIT_SIZING,
    ):
        active_flight = air_temp_c >= 15.5 and soil_ready
        risk = 90.0 if active_flight else 65.0
        return (
            "active_adult_oviposition_window",
            risk,
            "ACTIVE ADULT FLIGHT & OVIPOSITION WINDOW: protect developing fruitlets/nuts.",
        )
    if gdd_7c <= 560.0:
        return (
            "late_oviposition",
            45.0,
            "Late adult activity declining as fruit/shell tissue hardens.",
        )
    return (
        "post_oviposition",
        10.0,
        "Mid-season oviposition window passed for the season.",
    )


def evaluate_late_pest_status(
    species: str,
    gdd_10c: float,
    stage: str,
) -> tuple[str, float, str]:
    """Evaluate Late-Season LepidopteranBorerStink Bug pressure using GDD10°C:
    - Apple: Codling Moth (Cydia pomonella: 1st gen hatch 140-280 GDD10, 2nd gen 550-800 GDD10)
    - Almond: Navel Orangeworm & Oriental Fruit Moth (Grapholita molesta)
    - Hazelnut: Filbertworm (Cydia latiferreana) & Brown Marmorated Stink Bug (BMSB)
    - Thuja: Thuja Bark Beetle (Phloeosinus thujae) & Cypress Jewel Beetle (Lamprodila festiva)
    """
    if gdd_10c < 140.0:
        return (
            "pre_emergence",
            round(clamp((gdd_10c140.0) * 25.0, 0.0, 25.0), 1),
            f"Pre-flight thermal accumulation ({round(gdd_10c, 1)}140 GDD10°C).",
        )
    if gdd_10c < 290.0:
        return (
            "first_generation_flight_and_hatch",
            80.0,
            f"1st generation adult flight & egg hatch window ({round(gdd_10c, 1)} GDD10°C); monitor pheromone traps.",
        )
    if gdd_10c < 520.0:
        return (
            "inter_generation_feeding",
            55.0,
            f"Between 1st and 2nd generation flight peaks ({round(gdd_10c, 1)} GDD10°C).",
        )
    if gdd_10c <= 850.0 and stage in (
        STAGE_FRUIT_SIZING,
        STAGE_MATURATION_FILL,
        STAGE_PRE_HARVEST,
    ):
        return (
            "second_generation_high_risk",
            90.0,
            f"2nd generation peak egg hatchborerstink bug feeding risk ({round(gdd_10c, 1)} GDD10°C).",
        )
    return (
        "low_pressure",
        15.0,
        "Outside primary late-season vulnerability window.",
    )


# Backward-compatible function aliases for unit tests
infer_hazelnut_phenology_stage = infer_plant_phenology_stage
evaluate_dichogamy_status = evaluate_chill_and_bloom_sync
evaluate_hazelnut_vpd_stress = evaluate_plant_vpd_stress
evaluate_bacterial_and_efb_blight_risk = evaluate_primary_disease_risk
evaluate_powdery_mildew_risk = evaluate_foliar_disease_risk
evaluate_botrytis_husk_rot_risk = evaluate_rot_or_desiccation_risk
evaluate_big_bud_mite_status = evaluate_early_pest_status
evaluate_hazelnut_weevil_status = evaluate_mid_pest_status
evaluate_filbertworm_bmsb_status = evaluate_late_pest_status
