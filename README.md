# City-building-database-of-China

City-scale building energy modeling workflow and replication materials for selected Chinese cities.

## Purpose

The data and code in this repository support the **peer review** of the manuscript submitted to *Nature Climate Change*:

**Fulfilling Spatially Heterogeneous Urban Heating Demand by Climate-Adaptive Electrification**

They are provided so reviewers and editors can verify methods, reproduce key workflow steps, and inspect city-level inputs and outputs described in the paper.

## Online resources

- **[National prototype building database](http://8.166.131.116/#/)**  
  Interactive web portal for simulation outputs from the national typical building database (China Building Energy Model Database).

- **[Shanghai building heating EUI visualization](http://8.138.56.183:8090/webgl/examples/webgl/shanghaiHeating.html)**  
  WebGL map of Shanghai showing building-level heating energy use intensity (EUI, kWh) by building type.

## Workflow overview

Building models are produced and simulated through the following pipeline:

```
GIS shapefile (.shp)  →  GIS2IDF  →  IDF settings  →  simulation-ready IDF  →  simulation results
```

| Stage | Description |
|-------|-------------|
| **GIS shapefile** | City building footprints and attributes in GIS vector format. |
| **GIS2IDF** | Geometry and metadata from GIS are converted into EnergyPlus IDF geometry and base objects. |
| **IDF settings** | Template-specific parameters (construction, HVAC, schedules, etc.) are applied to each building IDF. |
| **Simulation-ready IDF** | Final IDF files checked and prepared for EnergyPlus runs. |
| **Results** | Post-processed simulation outputs (e.g., EUI, end-use breakdown) for analysis and visualization. |

## Data in this repository

This repository provides materials for three pilot cities:

| City | GIS / building data | Weather file |
|------|---------------------|--------------|
| **Nanjing** | Included | Included |
| **Shanghai** | Included | Included |
| **Wuhan** | Included | Included |

*(Paths and file naming will be documented once data are uploaded.)*

Weather files are paired with each city so that simulations use consistent local climate inputs.

## Code organization

Scripts are split into modules to match the workflow and to support **quality checks** at each step:

| Module | Role |
|--------|------|
| **`GIS2IDF`** | Shapefile ingestion, footprint processing, and initial IDF generation from GIS. |
| **`idf_settings`** | Assignment and editing of IDF templates, constructions, systems, and run parameters. |

Additional utilities (batch runs, result aggregation, QC reports) will be added as the codebase is finalized.

Suggested layout (to be populated with your scripts):

```
├── data/
│   ├── nanjing/
│   ├── shanghai/
│   └── wuhan/
├── GIS2IDF/
├── idf_settings/
└── (results / docs as needed)
```

## Replication notes

1. Start from city GIS inputs under `data/`.
2. Run **GIS2IDF** to generate base IDFs.
3. Run **idf_settings** to produce simulation-ready IDFs.
4. Execute EnergyPlus (external) with the provided weather files.
5. Compare outputs with published figures or the online visualizations above.

## Status

- README and workflow description: current.
- City data, weather files, and code modules: **to be added** in upcoming commits.

## Citation

*(Add paper / database citation when available.)*

## License

*(Add license when decided.)*
