# Plant & Orchard Metrics (`plant_metrics`)

[![Validate Hassfest & HACS](https://github.com/ofedotov/plant-metrics/actions/workflows/validate.yml/badge.svg)](https://github.com/ofedotov/plant-metrics/actions/workflows/validate.yml)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom **Home Assistant** integration that transforms weather station and soil/canopy sensor data (such as **Ecowitt** outdoor suites, **WH51** soil moisture sensors, and **WN31/WH34** temperature probes) into real-time agronomic, phenological, irrigation, frost, and pest/disease metrics for orchard, nursery, and landscape plants.

---

## Supported Plant Species & Cultivars

- **Hazelnut (*Corylus avellana*)**:
  - *Tonda di Giffoni*, *Tonda Gentile Romana*, *Tonda Francescana*, *Tonda Gentile delle Langhe*, *Barcelona*, *Jefferson (EFB Resistant)*, *Hall's Giant*, *Nursery Stoolbed / Layering Bed*
- **Apple (*Malus domestica*)**:
  - *Gala*, *Honeycrisp*, *Golden Delicious*, *Granny Smith*, *Antonovka*, *Renet Simirenko*
- **Almond (*Prunus dulcis*)**:
  - *Nonpareil*, *Tuono (Self-Fertile)*, *Ferragnès*, *Nikitsky 62*, *Foros*, *Standard / Multi-Cultivar*
- **Sweet Cherry (*Prunus avium*)**:
  - *Bigarreau Burlat*, *Regina*, *Kordia*, *Standard / Multi-Cultivar*
- **Thuja & Container Conifers (*Thuja occidentalis* & Conifers)**:
  - *Smaragd*, *Brabant*, *Columna*, *Danica*, *Container Liner P9 (0.5 L)*, *Container Pot P11 (1 L)*, *Container Pot C3 (3 L)*
- **Custom / Generic Plant**:
  - Fully user-configurable chill targets, GDD base/upper thresholds, canopy area, and root-zone depth.

---

## Two-Tier Architecture

1. **Weather Station Hub (`weather_hub`)**
   - Binds to your weather station entities (Temperature, Humidity, Wind Speed, Wind Gust, Solar Radiation, Barometric Pressure, Rain Rate, Daily Rain, UV Index, Elevation). Multiple hubs can be configured for different microclimate zones.
   - Computes site-wide psychrometric, radiative, spray, pollination, and evapotranspiration metrics:
     - **Wet-Bulb Temperature ($T_w$, °C)** via Stull (2011) for radiative frost protection
     - **Dew Point Temperature ($T_d$, °C)** & **Dew Point Depression (°C)**
     - **Air VPD (kPa)** & daily peak VPD
     - **Spray $\Delta T$ (°C)**, **Foliar Spray Suitability Score (`%`)**, and **Foliar Spray Window Suitable** binary sensor
     - **Photosynthetic Photon Flux Density ($\text{PPFD}$, $\mu\text{mol/m}^2/\text{s}$)** & **Daily Light Integral ($\text{DLI}$, $\text{mol/m}^2/\text{d}$)**
     - **Hourly & Daily Reference Evapotranspiration ($\text{ET}_0$, mm/h & mm)** via ASCE / FAO-56 Penman-Monteith
     - **Virtual Leaf Wetness (`%`)**, **Continuous Leaf Wetness Duration (h)**, and **Foliage Wet** binary sensor
     - **Wind Pollination Suitability Score (`%`)** (for Hazelnut, Thuja, conifers) & **Bee / Insect Pollination Suitability Score (`%`)** (for Apple, Almond, Sweet Cherry, stone/pome fruit)

2. **Plant / Orchard Blocks (`plant_block`, 1..N blocks)**
   - Links to a parent Weather Hub and adds a **Plant Species & Cultivar Profile** plus optional block-specific **WH51** soil moisture sensors and **WN31/WH34** root-zone/canopy temperature probes.
   - Computes species- and cultivar-specific metrics:
     - **Thermal & Phenology**:
       - Cumulative **Chill Hours ($0\text{--}7.2\,^\circ\text{C}$)** & **Utah Chill Units (CU)**
       - **Primary Bud Chill Fulfillment (`%`)** & **Pollinizer / Catkin Chill Fulfillment (`%`)**
       - **Bloom & Pollination Sync Status** (detects protandry / pollinizer mismatch in warm winters)
       - Species-aware **Pollination Activity Score (`%`)** (wind or bee/insect flight model)
       - **Seasonal Growing Degree Days ($\text{GDD}$)** with configurable $T_{\text{base}}$ and $T_{\text{upper}}$
       - Automatic or manual **Plant Phenology Stage** (`select` + `switch`)
     - **Water Balance & Canopy Stress**:
       - **Canopy Leaf Temperature (°C)** (measured from shaded WN31 probe or modeled via leaf energy balance)
       - **Canopy Leaf VPD (kPa)** & species-specific **Stomatal & VPD Stress Status** (`optimal`, `moderate_closure`, `high_stress`, `leaf_scorch_risk`)
       - Stage- and species-specific **Crop Coefficient ($K_c$)** & **Daily Crop Evapotranspiration ($\text{ET}_c$, mm)**
       - **Daily Plant Water Demand (L/plant)** & **Daily Block Total Water Demand (L/block)**
       - **Root-Zone Water Deficit (mm)**, **Root-Zone Depletion (`%`)**, **Recommended Irrigation Dose per Plant (L)**, and **Irrigation Needed** alert
     - **Stage-Aware Frost & Species Disease / Pest Models**:
       - **Stage-Aware Frost Damage Risk** (`none`, `watch`, `warning`, `critical_damage`) using species-specific critical bud/flower/fruitlet temperatures
       - **Primary Blight & Scab Risk (`%`)**: Apple Scab (*Venturia inaequalis* Mills model) & Fire Blight, Almond & Cherry Blossom Blight (*Monilinia*) & Shot Hole / Leaf Spot (*Blumeriella*), Hazelnut Bacterial & Eastern Filbert Blight, Thuja Phomopsis & Kabatina Tip Blight
       - **Foliar Mildew & Leaf/Needle Disease Risk (`%`)**: Powdery Mildew, Almond Leaf Curl & Rust, Thuja Needle Blight / Shütte (*Didymascella*)
       - **Fruit Rot & Winter Desiccation Risk (`%`)**: Monilinia/Botrytis/Hull Rot, Sweet Cherry Rain-Induced Cracking Risk, and **Thuja / Conifer Winter Sunscald / Physiological Desiccation**
       - **Early-Season Pest Status ($\text{GDD}_{6.0}$)**: Hazelnut Big Bud Mite, Apple Blossom Weevil, Almond Peach Twig Borer, Black Cherry Aphid, Thuja Leafminer & Scale
       - **Mid-Season Pest Status ($\text{GDD}_{7.0}$ + Soil Temp / VPD)**: Hazelnut Weevil, Apple Sawfly, Almond Seed Wasp, European Cherry Fruit Fly (*Rhagoletis cerasi*), Conifer Spider Mite
       - **Late-Season Pest Status ($\text{GDD}_{10.0}$)**: Apple Codling Moth, Almond Oriental Fruit Moth, Cherry Spotted Wing Drosophila (*Drosophila suzukii*), Hazelnut Filbertworm & BMSB, Thuja Bark & Jewel Beetles

---

## Installation via HACS

1. Open **HACS** (or **Marketplace**) in Home Assistant.
2. Add custom repository `https://github.com/ofedotov/plant-metrics` with category **Integration**.
3. Install **Plant & Orchard Metrics** and restart Home Assistant.
4. Go to **Settings -> Devices & Services -> Add Integration -> Plant & Orchard Metrics**:
   - First configure your **Weather Station Hub**.
   - Then add one or more **Plant / Orchard Blocks**.
