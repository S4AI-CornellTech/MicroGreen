import streamlit as st
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
import matplotlib.cm as cm
import os

from constants import * 
from helper import *
from solar_only import *
from battery_only import *
from hybrid import *

from Mobisys_solar_plots import solar_plot
from Mobisys_battery_plots import battery_plot
from Mobisys_lifetime_plots import lifetime_plot

##########################################################################################
plt.rcParams["xtick.labelsize"] = 8

##########################################################################################
st.set_page_config(layout="wide")

##########################################################################################
# Load dataset
curr_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
csv_path = "database/profiling_results.csv" 
df = pd.read_csv(csv_path)

##########################################################################################
# Drop rows with missing data for all required fields
trimmed_df = df.dropna(subset=[
    "inference energy (mJ)",
    "Total Processing Time (us)",
    "kg CO2e (capacitor only)",
    "number of capacitors",
    "minimum supply voltage (V_L)",
    "maximum supply voltage (V_H)"
])

# Clean and convert 'Total Processing Time (us)'
trimmed_df["Total Processing Time (us)"] = (
    trimmed_df["Total Processing Time (us)"]
    .astype(str)
    .str.replace(",", "", regex=False)
)
trimmed_df["Total Processing Time (us)"] = pd.to_numeric(
    trimmed_df["Total Processing Time (us)"], errors="coerce"
)

# Rename voltage columns
trimmed_df = trimmed_df.rename(columns={
    "minimum supply voltage (V_L)": "Vl",
    "maximum supply voltage (V_H)": "Vh"
})

# Create device-model pairs
device_models = trimmed_df[["Devices", "Model"]].drop_duplicates()

##########################################################################################
# Argparse for command-line options
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", choices=["kws-s", "kws-l", "ppd-s", "ppd-l"], default=None)
    parser.add_argument("--solar-plot-gen", action="store_true", default=None)
    parser.add_argument("--battery-plot-gen", action="store_true", default=None)
    parser.add_argument("--lifetime-plot-gen", action="store_true", default=None)
    parser.add_argument("--inference-per-second", type=float, default=None)
    parser.add_argument("--lifetime-years", type=float, default=None)

    # Streamlit passes its own args, so ignore unknown ones
    args, _ = parser.parse_known_args()
    return args

args = parse_args()

solar_plot_gen = args.solar_plot_gen if args.solar_plot_gen else False
battery_plot_gen = args.battery_plot_gen if args.battery_plot_gen else False
lifetime_plot_gen = args.lifetime_plot_gen if args.lifetime_plot_gen else False

##########################################################################################
# Knob settings

with st.sidebar:
    solar_energy_harvesting = st.checkbox("Use Solar Energy Harvesting", value=True)
    battery_powered = st.checkbox("Use Battery Power", value=True)
    hybrid_power_mode = st.checkbox("Use Both (Hybrid Power Mode)", value=True)

    workload = args.workload if args.workload is not None else st.selectbox("Select Workload", options=["kws-s", "kws-l", "ppd-s", "ppd-l"], index=1)
    inference_per_second = args.inference_per_second if args.inference_per_second is not None else st.slider("Inferences Per Second", min_value=0.1, max_value=30.0, value=0.01, step=0.1)
    lifetime_years = args.lifetime_years if args.lifetime_years is not None else st.slider("Deployment Lifetime (Years)", min_value=0.2, max_value=5.0, value=2.0, step=0.1)
    if solar_energy_harvesting or hybrid_power_mode:
        irradiance = st.slider("Irradiance (uW/cm²)", min_value=10, max_value=100000, value=1000, step=10)
    else:
        irradiance = 1000 # stub

    if hybrid_power_mode:
        solar_panel_area_cap = st.slider("Max Solar Panel Area (cm²)", min_value=1, max_value=2000, value=200, step=1)

##########################################################################################
workload_df = trimmed_df[trimmed_df["Model"] == workload].copy()

if solar_energy_harvesting:

    workload_df_solar = run_solar_harvesting_analysis(
        workload_df,
        workload,
        irradiance,
        inference_per_second,
        lifetime_years,
    )

    solar_analysis_plots(workload_df_solar, workload, inference_per_second, irradiance, lifetime_years)

    # below are function calls that generate Mobisys solar plot
    indoor_workload_df_solar = run_solar_harvesting_analysis(
        workload_df,
        "kws-l",
        irradiance=50,
        inference_per_second=1,
        lifetime_years=1,
    )
    outdoor_workload_df_solar = run_solar_harvesting_analysis(
        workload_df,
        "kws-l",
        irradiance=60000,
        inference_per_second=1,
        lifetime_years=1,
    )

    if solar_plot_gen:
        solar_plot(indoor_workload_df_solar, outdoor_workload_df_solar)

    # below are function calls that generate Mobisys lifetime plot
    lifetime_workload_df_solar = run_solar_harvesting_analysis(
        workload_df,
        'kws-l',
        400,
        6,
        5,
    )


if battery_powered:

    workload_df_battery = run_battery_powered_analysis(
        workload_df,
        workload,
        inference_per_second,
        lifetime_years,
    )

    battery_analysis_plots(workload_df_battery, workload, inference_per_second, lifetime_years)

    # # below are function calls that generate Mobisys battery plot

    low_ips_workload_df_battery = run_battery_powered_analysis(
        workload_df,
        "kws-s",
        inference_per_second=0.1,
        lifetime_years=5,
    )

    high_ips_workload_df_battery = run_battery_powered_analysis(
        workload_df,
        "kws-s",
        inference_per_second=10.0,
        lifetime_years=5,
    )

    if battery_plot_gen:
        battery_plot(low_ips_workload_df_battery, high_ips_workload_df_battery)

    # below are function calls that generate Mobisys lifetime plot
    lifetime_workload_df_battery = run_battery_powered_analysis(
        workload_df,
        'kws-l',
        6,
        5,
    )

if hybrid_power_mode:

    workload_df_hybrid = run_hybrid_powered_analysis(
        workload_df,
        workload,
        irradiance,
        inference_per_second,
        solar_panel_area_cap,
        lifetime_years,
    )

    # below are function calls that generate Mobisys lifetime plot
    lifetime_workload_df_hybrid = run_hybrid_powered_analysis(
        workload_df,
        'kws-l',
        400,
        6,
        275,
        5,
    )

    if lifetime_plot_gen:
        lifetime_plot(lifetime_workload_df_solar, lifetime_workload_df_battery, lifetime_workload_df_hybrid)
    


# ===============================
# Total Carbon Emissions vs monetary cost scatter plot
# ===============================

# if solar_energy_harvesting or battery_powered:
st.subheader("Total Carbon Emissions vs Monetary Cost")

fig_cost, ax_cost = plt.subplots(figsize=(5, 3))

# Create unique device list and assign colors using matplotlib colormap
if 'solar_energy_harvesting' in locals() and solar_energy_harvesting and 'battery_powered' in locals() and battery_powered:
    all_devices = pd.concat([workload_df_solar, workload_df_battery])["Devices"].unique()
elif 'solar_energy_harvesting' in locals() and solar_energy_harvesting:
    all_devices = workload_df_solar["Devices"].unique()
elif 'battery_powered' in locals() and battery_powered:
    all_devices = workload_df_battery["Devices"].unique()
elif 'hybrid_power_mode' in locals() and hybrid_power_mode:
    all_devices = workload_df_hybrid["Devices"].unique()
device_color_map = {device: device_colors[device] for device in all_devices}


# Solar-powered devices (circle marker)
if 'solar_energy_harvesting' in locals() and solar_energy_harvesting and not workload_df_solar.empty:
    for device, group in workload_df_solar.groupby("Devices"):
        ax_cost.scatter(
            group["total embodied carbon (kg CO2e)"],
            group["total monetary cost ($)"],
            label=f"{device} (Solar)",
            color=device_color_map[device],
            marker="o"
        )

# Battery-powered devices (x marker)
if 'battery_powered' in locals() and battery_powered and not workload_df_battery.empty:
    for device, group in workload_df_battery.groupby("Devices"):
        ax_cost.scatter(
            group["total embodied carbon (kg CO2e)"],
            group["total monetary cost ($)"],
            label=f"{device} (Battery)",
            color=device_color_map[device],
            marker="x"
        )

# Hybrid-powered devices (triangle marker)
if 'hybrid_power_mode' in locals() and hybrid_power_mode and not workload_df_hybrid.empty:
    for device, group in workload_df_hybrid.groupby("Devices"):
        ax_cost.scatter(
            group["total embodied carbon (kg CO2e)"],
            group["total monetary cost ($)"],
            label=f"{device} (Hybrid)",
            color=device_color_map[device],
            marker="^"
        )

ax_cost.set_xlabel("Total Carbon Emissions (kg CO₂e)")
ax_cost.set_ylabel("Monetary Cost ($)")
ax_cost.set_title(f"Total Carbon Emissions vs Monetary Cost for {workload}")
ax_cost.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
ax_cost.grid(True)

st.pyplot(fig_cost)
if GENERATE_PLOTS:
    fig_cost.savefig("figures/total_carbon_vs_monetary_cost.pdf", dpi=300)

# ===============================
# Lifetime vs. Total Carbon Emissions Plot
# ===============================

if solar_energy_harvesting or battery_powered:
    st.subheader("Total Carbon Emissions Over Deployment Lifetime")

    max_lifetime_years = 3
    # max_lifetime_years = 0.15
    lifetime_years = np.arange(0, max_lifetime_years, 0.005)  # integer years for clarity

    fig_life, ax_life = plt.subplots(figsize=(5, 3))

    # Solar-powered: total carbon is constant (embodied carbon only)
    if 'solar_energy_harvesting' in locals() and solar_energy_harvesting and not workload_df_solar.empty:
        for _, row in workload_df_solar.iterrows():
            total_carbon = row["total embodied carbon (kg CO2e)"]
            ax_life.plot(lifetime_years, [total_carbon] * len(lifetime_years), label=f"{row['Devices']} (solar)", linestyle=":", color=device_color_map[row['Devices']])

    # Battery-powered: carbon increases with battery usage over time
    if 'workload_df_battery' in locals() and battery_powered and not workload_df_battery.empty:
        for _, row in workload_df_battery.iterrows():
            board_carbon = row["board embodied carbon (kg CO2e)"]
            battery_carbon_per_year = row["battery carbon per year (kg CO2e)"]
            total_carbon_over_time = board_carbon + battery_carbon_per_year * lifetime_years
            ax_life.plot(lifetime_years, total_carbon_over_time, label=f"{row['Devices']} (battery)", linestyle="-", color=device_color_map[row['Devices']])
    # Hybrid-powered: carbon increases with battery usage over time, but at a reduced rate
    if 'workload_df_hybrid' in locals() and hybrid_power_mode and not workload_df_hybrid.empty:
        for _, row in workload_df_hybrid.iterrows():
            embodied_carbon = row["total embodied carbon (kg CO2e)"]
            battery_carbon_per_year = row["hybrid battery carbon over lifetime (kg CO2e)"]
            total_carbon_over_time = embodied_carbon + battery_carbon_per_year * lifetime_years
            ax_life.plot(lifetime_years, total_carbon_over_time, label=f"{row['Devices']} (hybrid)", linestyle="-.", color=device_color_map[row['Devices']])

    ax_life.set_xticklabels([f"{int(tick*12*7)}" for tick in ax_life.get_xticks()])  # convert years to months
    ax_life.set_xlabel("Deployment Lifetime (weeks)")
    ax_life.set_ylabel("Cumulative Carbon Emissions (kg CO$_2$e)")
    ax_life.set_title(f"Total Carbon Emissions vs.    Lifetime for {workload}")
    ax_life.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax_life.grid(True)
    ax_life.set_yscale("log")
    st.pyplot(fig_life)
    if GENERATE_PLOTS:
        fig_life.savefig("figures/total_carbon_over_lifetime.pdf", dpi=300)

    st.markdown(
        "_This chart shows total carbon emissions over time. Solar-powered devices incur a one-time embodied carbon cost, while battery-powered devices accumulate additional emissions each year due to battery use._"
    )












    


