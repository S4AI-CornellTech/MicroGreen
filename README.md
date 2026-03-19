# MicroGreen

MicroGreen, a design space exploration framework for sustainable edge devices. MicroGreen integrates embodied-carbon modeling, workload characterization, and environment-dependent operational analysis. It incorporates parametric embodied-carbon models for MCUs, sensors, regulators, storage, batteries, capacitors, and solar panels, leveraging LCA databases. Using these models, MicroGreen takes as input application requirements (e.g., workload, duty cycle, deployment lifetime) and environmental traces (e.g., solar availability) and identifies carbon-optimal configurations. We empirically characterize a repository of MCUs under diverse workloads, integrate peripheral and power-source options, and generate Pareto-optimal designs to illustrate trade-offs between carbon footprint, performance, and cost

![Image of the MicroGreen framework](img/framework.svg)

---
### Setup

1. Recursively clone the repo
<!-- TODO: talk about setting up: clone repo, setup.sh -->
```bash
git clone --recurse-submodules git@github.com:S4AI-CornellTech/MicroGreen.git
```

<!-- TODO: repo structure: take about the modeling and profiling part of the artefact evaluation -->

### Reproducing Key Result Figures in MicroGren

Figure 3 - Board Carbon Breakdown 
```bash
python3 scripts/carbon_component_composition_plotter.py
```
Figure 5 - Per Inference Runtime and Energy Plot
```bash
python3 scripts/characterization_fig.py
```
Figure 6 - Carbon Rank Plot
```bash
python3 scripts/overall_eval_carbon.py --lifetime-years 1 --solar-panel-area-cap 611
```
Figure 7 - Irradiance Analysis Plot
```bash
python3 framework/main.py --workload kws-l --solar-plot
```
Figure 8 - Battery Analysis Plot
```bash
python3 framework/main.py --workload kws-s --battery-plot
```
Figure 10 - Hybrid Analysis Plot
```bash
python3 framework/main.py --workload kws-l --lifetime-plot
```

### Carbon Modeling Verification

<!-- TODO: talk about the pipeline of automatically connect carbon modeling to database and to constants.py -->
```
python3 scripts/board_carbon_csv_generator.py \
  EmbodiedCarbonModeling/ouputs/coralDevMicro_output \
  EmbodiedCarbonModeling/ouputs/ESP32_output \
  EmbodiedCarbonModeling/ouputs/ESP32-C6_output \
  EmbodiedCarbonModeling/ouputs/ESP32-S3_output \
  EmbodiedCarbonModeling/ouputs/nRF52840_output \
  EmbodiedCarbonModeling/ouputs/RP2040_output \
  EmbodiedCarbonModeling/ouputs/RP2350_output \
  EmbodiedCarbonModeling/ouputs/STM32F411_output \
  -o database/board_carbon.csv 
```