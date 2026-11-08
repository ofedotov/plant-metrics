"""Unit tests for Plant & Orchard Metrics agronomic and psychrometric calculations."""

from __future__ import annotations

import unittest

from custom_components.plant_metrics.calculations import (
    calc_air_vpd_kpa,
    calc_canopy_vpd_kpa,
    calc_delta_t_c,
    calc_dew_point_c,
    calc_dli_increment_mol,
    calc_fao56_hourly_et0_mm,
    calc_gdd_increment,
    calc_ppfd_umol,
    calc_utah_chill_rate,
    calc_virtual_leaf_wetness_pct,
    calc_wet_bulb_c,
    estimate_canopy_temperature_c,
    evaluate_chill_and_bloom_sync,
    evaluate_early_pest_status,
    evaluate_foliar_disease_risk,
    evaluate_insect_pollination_window,
    evaluate_late_pest_status,
    evaluate_mid_pest_status,
    evaluate_plant_vpd_stress,
    evaluate_primary_disease_risk,
    evaluate_rot_or_desiccation_risk,
    evaluate_spray_window,
    evaluate_stage_frost_risk,
    evaluate_wind_pollination_window,
    infer_plant_phenology_stage,
    is_chill_hour,
)
from custom_components.plant_metrics.const import (
    SPECIES_ALMOND,
    SPECIES_APPLE,
    SPECIES_HAZELNUT,
    SPECIES_SWEET_CHERRY,
    SPECIES_THUJA,
    STAGE_BLOOM,
    STAGE_BUD_SWELL,
    STAGE_DORMANT,
    STAGE_FRUIT_SIZING,
    STAGE_MATURATION_FILL,
    STAGE_PETAL_FALL_LEAF_OUT,
    STAGE_SHOOT_GROWTH,
)
from custom_components.plant_metrics.plants import PLANT_PROFILES, get_plant_profile


class TestPlantMetricsCalculations(unittest.TestCase):
    """Test suite for pure agronomic calculation functions."""

    def test_plant_profiles_catalog(self) -> None:
        """Verify Hazelnut, Apple, Almond, Sweet Cherry, and Thuja profiles exist and load."""
        species_found = {p.species for p in PLANT_PROFILES.values()}
        self.assertIn(SPECIES_HAZELNUT, species_found)
        self.assertIn(SPECIES_APPLE, species_found)
        self.assertIn(SPECIES_ALMOND, species_found)
        self.assertIn(SPECIES_SWEET_CHERRY, species_found)
        self.assertIn(SPECIES_THUJA, species_found)

        self.assertEqual(get_plant_profile("apple_antonovka").species, SPECIES_APPLE)
        self.assertEqual(get_plant_profile("almond_nonpareil").species, SPECIES_ALMOND)
        self.assertEqual(
            get_plant_profile("sweet_cherry_regina").species, SPECIES_SWEET_CHERRY
        )
        self.assertEqual(get_plant_profile("thuja_smaragd").species, SPECIES_THUJA)
        self.assertEqual(
            get_plant_profile("hazelnut_tonda_di_giffoni").species, SPECIES_HAZELNUT
        )

    def test_psychrometrics_wet_bulb_and_dew_point(self) -> None:
        """Verify wet-bulb, dew point, VPD, and Delta-T calculations."""
        tw = calc_wet_bulb_c(2.0, 40.0)
        td = calc_dew_point_c(2.0, 40.0)
        self.assertLess(tw, 0.0)
        self.assertLess(td, tw)

        vpd = calc_air_vpd_kpa(25.0, 50.0)
        self.assertAlmostEqual(vpd, 1.584, places=2)

        dt = calc_delta_t_c(20.0, calc_wet_bulb_c(20.0, 55.0))
        self.assertGreater(dt, 4.0)
        self.assertLess(dt, 7.0)

    def test_canopy_temperature_and_vpd_stress(self) -> None:
        """Verify canopy energy balance and VPD stress classification across species."""
        t_canopy_hot = estimate_canopy_temperature_c(
            air_temp_c=33.0, rh_pct=28.0, solar_rad_wm2=850.0, wind_speed_ms=0.8
        )
        self.assertGreater(t_canopy_hot, 33.0)
        vpd_canopy = calc_canopy_vpd_kpa(33.0, 28.0, t_canopy_hot)
        state, _ = evaluate_plant_vpd_stress(vpd_canopy, t_canopy_hot, 18.0)
        self.assertEqual(state, "leaf_scorch_risk")

        t_canopy_mild = estimate_canopy_temperature_c(
            air_temp_c=22.0, rh_pct=65.0, solar_rad_wm2=400.0, wind_speed_ms=2.5
        )
        vpd_mild = calc_canopy_vpd_kpa(22.0, 65.0, t_canopy_mild)
        state_mild, _ = evaluate_plant_vpd_stress(vpd_mild, t_canopy_mild, 9.0)
        self.assertEqual(state_mild, "optimal")

    def test_fao56_hourly_et0_and_par(self) -> None:
        """Verify FAO-56 Penman-Monteith hourly ET0 and PPFD/DLI."""
        et0_midday = calc_fao56_hourly_et0_mm(
            temp_c=28.0,
            rh_pct=42.0,
            wind_speed_ms=2.5,
            solar_rad_wm2=780.0,
            pressure_kpa=100.2,
            elevation_m=150.0,
        )
        self.assertGreater(et0_midday, 0.40)
        self.assertLess(et0_midday, 0.90)

        ppfd = calc_ppfd_umol(500.0)
        self.assertAlmostEqual(ppfd, 1020.0, places=1)
        dli_1h = calc_dli_increment_mol(ppfd, 3600.0)
        self.assertAlmostEqual(dli_1h, 3.672, places=3)

    def test_chill_and_bloom_sync_models(self) -> None:
        """Verify Chill Hours, Utah Model, and Bloom Sync / Dichogamy detection."""
        self.assertTrue(is_chill_hour(5.0))
        self.assertFalse(is_chill_hour(-1.0))
        self.assertEqual(calc_utah_chill_rate(6.0), 1.0)
        self.assertEqual(calc_utah_chill_rate(20.0), -1.0)

        status, attrs = evaluate_chill_and_bloom_sync(
            chill_units=480.0,
            primary_target=680.0,
            secondary_target=450.0,
            current_stage=STAGE_BUD_SWELL,
            species=SPECIES_HAZELNUT,
        )
        self.assertEqual(status, "bloom_sync_mismatch_risk")
        self.assertEqual(attrs["secondary_chill_fulfillment_pct"], 100.0)
        self.assertLess(attrs["primary_chill_fulfillment_pct"], 80.0)

    def test_phenology_and_stage_frost_risk_across_species(self) -> None:
        """Verify stage inference and species-specific frost risk thresholds."""
        stage = infer_plant_phenology_stage(
            utah_chill_units=720.0,
            primary_chill_target=600.0,
            secondary_chill_target=600.0,
            gdd=250.0,
            month=4,
            species=SPECIES_APPLE,
        )
        self.assertEqual(stage, STAGE_PETAL_FALL_LEAF_OUT)

        # Almond small nutlet at -1.2°C wet-bulb is critical damage (threshold -1.1°C)
        almond_risk, _ = evaluate_stage_frost_risk(
            wet_bulb_c=-1.2,
            canopy_temp_c=-1.3,
            stage=STAGE_PETAL_FALL_LEAF_OUT,
            species=SPECIES_ALMOND,
        )
        self.assertEqual(almond_risk, "critical_damage")

        # Thuja in winter dormancy at -15°C is completely safe (critical is -30°C)
        thuja_risk, _ = evaluate_stage_frost_risk(
            wet_bulb_c=-15.0,
            canopy_temp_c=-15.0,
            stage=STAGE_DORMANT,
            species=SPECIES_THUJA,
        )
        self.assertEqual(thuja_risk, "none")

    def test_wind_and_insect_pollination_and_spray_windows(self) -> None:
        """Verify spray window, wind pollination (Hazelnut/Thuja), and bee pollination (Apple/Almond)."""
        ok_spray, score_spray, _ = evaluate_spray_window(
            delta_t_c=4.5,
            wind_speed_kmh=8.0,
            wind_gust_kmh=12.0,
            rain_rate_mmh=0.0,
            temp_c=16.0,
        )
        self.assertTrue(ok_spray)
        self.assertGreaterEqual(score_spray, 85.0)

        # Wind pollination favorable at 11°C, 55% RH, 12 km/h wind
        ok_wind, score_wind, _ = evaluate_wind_pollination_window(
            temp_c=11.0, rh_pct=55.0, wind_speed_kmh=12.0, rain_rate_mmh=0.0
        )
        self.assertTrue(ok_wind)
        self.assertGreater(score_wind, 70.0)

        # Bee pollination favorable at 18°C, 55% RH, 8 km/h wind, 450 W/m² solar
        ok_bee, score_bee, _ = evaluate_insect_pollination_window(
            temp_c=18.0,
            rh_pct=55.0,
            wind_speed_kmh=8.0,
            rain_rate_mmh=0.0,
            solar_rad_wm2=450.0,
        )
        self.assertTrue(ok_bee)
        self.assertGreater(score_bee, 80.0)

    def test_multi_species_pest_and_disease_models(self) -> None:
        """Verify Apple Scab, Thuja Winter Sunscald, and GDD pest models."""
        wet_pct = calc_virtual_leaf_wetness_pct(
            temp_c=16.0,
            dew_point_c=15.5,
            rh_pct=96.0,
            rain_rate_mmh=1.2,
            solar_rad_wm2=20.0,
            wind_speed_ms=0.5,
            prev_wetness_pct=50.0,
            dt_seconds=3600.0,
        )
        self.assertEqual(wet_pct, 100.0)

        # Apple Scab high infection risk at 18°C after 12h continuous leaf wetness during bloom
        scab_pct, scab_lvl, _ = evaluate_primary_disease_risk(
            species=SPECIES_APPLE,
            lwd_hours=12.0,
            temp_c=18.0,
            rain_daily_mm=8.0,
            stage=STAGE_BLOOM,
            susceptibility=1.1,
        )
        self.assertGreaterEqual(scab_pct, 70.0)
        self.assertEqual(scab_lvl, "severe")

        # Thuja winter sunscald / physiological desiccation when soil is frozen (1°C) and sunny (550 W/m²)
        thuja_desiccation_pct, _ = evaluate_rot_or_desiccation_risk(
            species=SPECIES_THUJA,
            lwd_hours=0.0,
            temp_c=4.0,
            rh_pct=40.0,
            solar_rad_wm2=550.0,
            wind_speed_ms=4.0,
            soil_temp_c=1.0,
            stage=STAGE_DORMANT,
        )
        self.assertGreaterEqual(thuja_desiccation_pct, 50.0)

        # Early pest peak treatment window at 175 GDD6°C
        early_status, _, _ = evaluate_early_pest_status(
            species=SPECIES_APPLE, gdd_6c=175.0, stage=STAGE_BUD_SWELL
        )
        self.assertEqual(early_status, "peak_migration_spray_window")

        # Mid pest active oviposition at 280 GDD7°C
        mid_status, _, _ = evaluate_mid_pest_status(
            species=SPECIES_HAZELNUT,
            gdd_7c=280.0,
            air_temp_c=20.0,
            soil_temp_c=15.0,
            canopy_vpd_kpa=0.9,
            stage=STAGE_SHOOT_GROWTH,
        )
        self.assertEqual(mid_status, "active_adult_oviposition_window")

        # Late pest (Codling Moth / Oriental Fruit Moth) 1st gen flight at 200 GDD10°C
        late_status, _, _ = evaluate_late_pest_status(
            species=SPECIES_APPLE, gdd_10c=200.0, stage=STAGE_FRUIT_SIZING
        )
        self.assertEqual(late_status, "first_generation_flight_and_hatch")


if __name__ == "__main__":
    unittest.main()
