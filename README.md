# City-building-database-of-China

City-scale building energy modeling workflow and replication materials for selected Chinese cities.

## Purpose

The data and code in this repository support the **peer review** of the manuscript submitted to *Nature Climate Change*:

**Fulfilling Spatially Heterogeneous Urban Heating Demand by Climate-Adaptive Electrification**

They are provided so reviewers and editors can verify methods, reproduce key workflow steps, and inspect city-level inputs and outputs described in the paper.

## Online resources

- **[National prototype building database](http://8.166.131.116/#/)**  
  Interactive web portal for simulation outputs from the national prototype building database (China Building Energy Model Database).

- **[Shanghai building heating EUI visualization](http://8.138.56.183:8090/webgl/examples/webgl/shanghaiHeating.html)**  
  WebGL map of Shanghai showing building-level heating energy use intensity (EUI, kWh) by building type.

## Workflow overview

Building models are produced and simulated through the following pipeline:

```
City GIS inputs  →  GIS2IDF  →  ready IDF  →  EnergyPlus simulation  →  results
```

| Stage | Description |
|-------|-------------|
| **City GIS inputs** | Building footprints and attributes, local weather, and building-parameter settings for each pilot city. |
| **GIS2IDF** | GIS data are turned into building EnergyPlus models (geometry and associated model setup). |
| **Ready IDF** | Per-building IDF files prepared for simulation. |
| **EnergyPlus simulation** | Batch runs using the city weather file(s). |
| **Results** | Simulation outputs for analysis and comparison with published figures or online visualizations. |

## Data in this repository

Materials are organized for three pilot cities:

| City | GIS / building data | Weather |
|------|---------------------|---------|
| **Nanjing** | Included | Included |
| **Shanghai** | Included | Included |
| **Wuhan** | Included | Included |

Weather includes baseline and scenario files aligned with each city where applicable.

## Code organization

Workflow scripts and working folders are under **`Script/`**:

| Item | Role |
|------|------|
| **`1_GIS2IDF.py`** | Generate ready IDF files from city GIS and input settings. |
| **`2_BatchSimulation.py`** | Run EnergyPlus in batch on ready IDF files and write outputs. |
| **`input/`** | GIS shapefiles, weather (EPW), and building-parameter settings. |
| **`ready_idf/`** | Generated IDF files by city (and demo subsets where provided). |
| **`result/`** | Simulation output folders. |

## Replication notes

1. Place or confirm city inputs under `Script/input/` (GIS, weather, settings).
2. Run **`1_GIS2IDF.py`** to produce IDFs under `Script/ready_idf/`.
3. Run **`2_BatchSimulation.py`** (with EnergyPlus installed locally) to simulate and obtain results under `Script/result/`.
4. Compare outputs with the paper and the online resources above.

## Status

- Workflow scripts, city inputs, sample ready IDFs, and demo results are included under `Script/`.
- Full national-scale extensions and additional QC utilities may be added as the release is finalized.

## Citation

*(Add paper / database citation when available.)*

## License

*(Add license when decided.)*
