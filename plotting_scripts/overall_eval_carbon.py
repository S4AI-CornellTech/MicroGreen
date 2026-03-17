# overall_eval.py
import os,sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from functools import partial
from matplotlib.lines import Line2D

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from framework.constants import * 

# =========================
# argument parsing
# =========================

def parse_args():
    parser = argparse.ArgumentParser(description="Solar panel energy calculator")
    parser.add_argument(
        "--lifetime-years",
        type=float,
        help="Lifetime of the solar panel in years",
    )
    parser.add_argument(
        "--solar-panel-area-cap",
        type=float,
        help="Solar panel area cap in cm²",
    )
    return parser.parse_args()

args = parse_args()
lifetime_years = args.lifetime_years
solar_panel_area_cap = args.solar_panel_area_cap

# =========================
# Experiment setup
# =========================
USE_CACHED_RESULTS = False

workloads = ["kws-s", "kws-l", "ppd-s", "ppd-l"]
irradiance_list = {  # µW/cm²
    "Dim": 200,
    "Medium": 10000,
    "Bright": 40000,
}
# inference per second range for each workloads
inferece_per_second_map = {
    "kws-s": np.arange(0.1, 15.0, 0.01),  # FPS
    "kws-l": np.arange(0.1, 15.0, 0.01),  # FPS
    "ppd-s": np.arange(0.1, 15.0, 0.1),   # FPS
    "ppd-l": np.arange(0.1, 30.0, 0.1),   # FPS
}

# lifetime_years = 1
# solar_panel_area_cap = 611.0  # cm²

if not USE_CACHED_RESULTS:
    ##########################################################################################
    # Load dataset
    curr_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
    path_to_profiling_results = "database/profiling_results.csv" 
    df = pd.read_csv(path_to_profiling_results)

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
    print("duplicate drops device:", trimmed_df["Devices"].unique())

    ##########################################################################################
    # Build workload_df_map
    ##########################################################################################
    # Normalize model names to lowercase and strip whitespace
    trimmed_df["Model"] = trimmed_df["Model"].astype(str).str.strip().str.lower()

    model_to_workload = {"kws-s", "kws-l", "ppd-s", "ppd-l"}

    # Drop rows that didn't match any known workload
    workload_df_master = trimmed_df.dropna(subset=["Model"]).copy()

    required_cols = ["Devices", "Total Processing Time (us)", "inference energy (mJ)", "number of capacitors", "Vl", "Vh", "Model", "kg CO2e (capacitor only)"]

    missing = [col for col in required_cols if col not in workload_df_master.columns]
    if missing:
        raise ValueError(f"Missing columns in trimmed_df: {missing}")

    # Split into per-workload DataFrames
    workload_df_map = {
        wl: workload_df_master.loc[workload_df_master["Model"] == wl, required_cols].copy()
        for wl in ["kws-s", "kws-l", "ppd-s", "ppd-l"]
    }

    # Diagnostic summary
    print("✅ workload_df_map generated successfully:")
    for wl, df_ in workload_df_map.items():
        print(f"  {wl}: {len(df_)} rows")

# =========================
# Helper functions
# =========================
SECONDS_PER_YEAR = 365 * 24 * 60 * 60

def calculate_energy_in_capacitors(n_caps, Vh, Vl, C_each_mF=0.47):
    """
    Energy stored in capacitors, returned in mJ.
    E = 0.5 * C_total * (Vh^2 - Vl^2)
    """
    C_mF_total = n_caps * C_each_mF
    E_mJ = 0.5 * C_mF_total * (Vh**2 - Vl**2)
    return E_mJ  # mJ

def calculate_solar_panel_area(inference_energy_mJ, irradiance, inference_per_second):
    """
    Your provided signature:
    - inference_energy_mJ: energy per inference (mJ)
    - irradiance: µW/cm²
    - inference_per_second: FPS
    Returns required solar panel area in cm².
    """
    energy_per_second_mJ = inference_energy_mJ * inference_per_second  # mJ/s
    power_per_second_uW = energy_per_second_mJ * 1000.0               # 1 mJ = 1000 µW·s
    area_cm2 = power_per_second_uW / (irradiance * solar_panel_efficiency)
    return area_cm2

def calculate_charging_time_per_inference(energy_in_capacitors_mJ, solar_panel_area_cm2, irradiance):
    # Calculate the charging time in seconds
    charging_time_s = energy_in_capacitors_mJ / ((irradiance / 1000) * solar_panel_efficiency * solar_panel_area_cm2) 
    return charging_time_s

def compute_embodied_carbon_table(
    workload_df: pd.DataFrame,
    irradiance_uW_cm2: float,
    inference_per_second: float,
) -> pd.Series:
    """
    Returns per-device total embodied carbon (kgCO2e) for the given irradiance and FPS.
    Index = device name.
    Expects workload_df to have columns:
      ["Devices", "inference energy (mJ)", "number of capacitors", "Vh", "Vl"]
    """
    df = workload_df.copy()

    # (Optional) capacitor energy; useful to keep for reporting
    df["energy in capacitors (mJ)"] = df.apply(
        lambda row: calculate_energy_in_capacitors(row["number of capacitors"], row["Vh"], row["Vl"]),
        axis=1
    )

    # Solar panel area (cm²), capped
    df["solar panel area (cm2)"] = df["inference energy (mJ)"].apply(
        lambda e: calculate_solar_panel_area(
            e, irradiance=irradiance_uW_cm2, inference_per_second=inference_per_second
        )
    )
    df["solar panel area capped (cm2)"] = df["solar panel area (cm2)"].clip(upper=solar_panel_area_cap)

    # Solar energy per second (mJ/s); note 1 µW = 0.001 mJ/s
    df["solar energy per second (mJ)"] = (
        df["solar panel area capped (cm2)"] * irradiance_uW_cm2 * solar_panel_efficiency * 1e-3
    )

    df["solar charging time per inference (s)"] = df.apply(
        lambda row: calculate_charging_time_per_inference(
            row["energy in capacitors (mJ)"],
            row["solar panel area capped (cm2)"],
            irradiance_uW_cm2
        ),
        axis=1
    )

    # number of inference in a second that is powered by solar energy
    df["number of inferences powered by solar per second"] = (
        df["solar energy per second (mJ)"] / df["inference energy (mJ)"]
    ).clip(upper=inference_per_second, lower=0)

    df["total time to do the specified ips (s)"] = inference_per_second * (df["Total Processing Time (us)"] * 1e-6)

    # need to calculate the number of cpacitor sets needed for each processor to achieve zero charging time
    # df["inference per capacitor set"] = 1 / df["solar charging time per inference (s)"]
    # df["number of capacitor sets needed"] = np.ceil(
    #     df["number of inferences powered by solar per second"] / df["inference per capacitor set"]
    # )
    df["number of capacitor sets needed"] = df["Total Processing Time (us)"] * 1e-6 /  df["solar charging time per inference (s)"] + 1

    # Battery energy per second (mJ/s)
    df["battery energy per second (mJ)"] = (inference_per_second - df["number of inferences powered by solar per second"]) * df["inference energy (mJ)"]

    # Battery consumption rate (AA / s)
    df["battery per second (AA)"] = df["battery energy per second (mJ)"] / 1000.0 / AA_energy

    # Batteries over lifetime and their carbon
    df["batteries needed over lifetime"] = df["battery per second (AA)"] * SECONDS_PER_YEAR * lifetime_years
    df["hybrid battery carbon over lifetime (kg CO2e)"] = df["batteries needed over lifetime"] * AA_carbon

    # Solar panel embodied carbon (for capped area)
    df["solar panel capped embodied carbon (kg CO2e)"] = df["solar panel area capped (cm2)"] * solar_panel_emission_per_cm2

    # Board + VR embodied carbon
    df["kg CO2e (board)"] = df["Devices"].map(whole_board_carbon).fillna(0.0)
    df["kg CO2e (voltage regulator)"] = df["Devices"].map(voltage_regulator_CO2).fillna(0.0)

    # Total embodied carbon
    df["total embodied carbon (kg CO2e)"] = (
        df["kg CO2e (board)"]
        + df["kg CO2e (voltage regulator)"]
        + df["solar panel capped embodied carbon (kg CO2e)"]
        + df["hybrid battery carbon over lifetime (kg CO2e)"]
        + df["kg CO2e (capacitor only)"] * df["number of capacitor sets needed"] * lifetime_years * 12
        + capacitor_switches_CO2e * (df["number of capacitor sets needed"] - 1)
    )

    # Invalidate entries where total time to do the specified ips exceeds 1 second
    df.loc[df["total time to do the specified ips (s)"] > 1.0, "total embodied carbon (kg CO2e)"] = np.nan

    # return df.set_index("Devices")["number of inferences powered by solar per second"]
    return df.set_index("Devices")["total embodied carbon (kg CO2e)"]

def _plot_rank_panel(ax, df, irr_label, irr_value, workload, yaxis_label=False, xaxis_label=False, title_label=False):
    """Render a single subplot with rank vs FPS."""

    if df.empty or df.shape[1] == 0 or df.shape[0] == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=11)
        ax.set_title(workload.upper(), fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.6)
        return []

    # Ranks per FPS column (1 = lowest carbon)
    rank_df = df.rank(axis=0, method="min", ascending=True)
    fps = pd.to_numeric(df.columns, errors="coerce").to_numpy(dtype=float)

    n_devices = len(df.index)
    for device in df.index:
        y = rank_df.loc[device].to_numpy(dtype=float)
        if np.all(np.isnan(y)):
            continue
        h, = ax.plot(fps, y, marker='.', linewidth=0.8, markersize=0.8, label=device, color=device_colors[device])

    if title_label:
        ax.set_title(workload.upper(), fontsize=9)
    if xaxis_label:
        ax.set_xlabel("IPS", fontsize=9)
        ax.tick_params(axis='x', labelsize=8)
    else:
        ax.set_xticklabels([])
    if yaxis_label:
        ax.set_ylabel(f"{irr_label}\n({irr_value/100} W/m²)", fontsize=9)
        ax.set_yticks([1, 2, 3, 4, 5, 6, 7, 8, 9])
        ax.tick_params(axis='y', labelsize=8)
    ax.set_ylim(n_devices + 0.5, 0.5)  # invert y so 1 is top
    ax.grid(True, linestyle='--', alpha=0.6)

def _plot_embodied_carbon_panel(ax, df, irr_label, irr_value, workload, yaxis_label=False, xaxis_label=False):
    """Render a single subplot with embodied carbon vs FPS."""

    if df.empty or df.shape[1] == 0 or df.shape[0] == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=11)
        ax.set_title(workload.upper(), fontsize=12, pad=10)
        ax.grid(True, linestyle='--', alpha=0.6)
        return

    fps = pd.to_numeric(df.columns, errors="coerce").to_numpy(dtype=float)

    for device in df.index:
        y = df.loc[device].to_numpy(dtype=float)
        if np.all(np.isnan(y)):
            continue
        ax.plot(fps, y, marker='.', linewidth=1.6, markersize=3, label=device, color =device_colors[device])

    ax.set_title(workload.upper(), fontsize=12, pad=10)
    # ax.set_yscale('log')
    ax.set_xlabel("Inference FPS")
    ax.set_ylabel(f"{irr_label} ({irr_value} µW/cm²)\nEmbodied Carbon (kg CO2e)")
    ax.grid(True, linestyle='--', alpha=0.6)

if not USE_CACHED_RESULTS: 
    # =========================
    # Supply workload data
    # =========================

    # Sanity check
    required_cols = {"Devices", "Total Processing Time (us)", "inference energy (mJ)", "number of capacitors", "Vh", "Vl"}
    for wl in workloads:
        if wl not in workload_df_map:
            raise ValueError(f"Missing workload dataframe for '{wl}' in workload_df_map.")
        missing = required_cols - set(workload_df_map[wl].columns)
        if missing:
            raise ValueError(f"[{wl}] missing columns: {missing}")

    # =========================
    # Generate results
    # =========================
    os.makedirs("intermediate_results", exist_ok=True)
    results = {wl: {} for wl in workloads}

    # devices = workload_df_master["Devices"].unique().tolist()
    # print("devices considered:", devices)

    for wl in workloads:
        wdf = workload_df_map[wl]
        devices = wdf["Devices"].tolist()
        template = pd.DataFrame(index=devices, columns=inferece_per_second_map[wl], dtype=float)

        for irr_label, irr_value in irradiance_list.items():
            result_df = template.copy()
            for ips in inferece_per_second_map[wl]:
                totals = compute_embodied_carbon_table(
                    workload_df=wdf,
                    irradiance_uW_cm2=float(irr_value),
                    inference_per_second=float(ips),
                )
                result_df[ips] = totals.reindex(result_df.index)
            results[wl][irr_label] = result_df
            result_df.to_csv(f"intermediate_results/{wl}_{irr_label}_embodied_carbon.csv")

    print("✅ Generated results[workload][irradiance_label] DataFrames and saved CSVs in ./intermediate_results/")

else:
    # Load cached results
    results = {wl: {} for wl in workloads}
    for wl in workloads:
        for irr_label in irradiance_list.keys():
            csv_path = f"intermediate_results/{wl}_{irr_label}_embodied_carbon.csv"
            if not os.path.isfile(csv_path):
                print(f"⚠️ Warning: Missing cached results file: {csv_path}")
                continue
            df = pd.read_csv(csv_path, index_col=0)
            results[wl][irr_label] = df
    print("✅ Loaded cached results from ./intermediate_results/")

# =========================
# Plot: 3 (rows = irradiance) × 4 (cols = workloads) rank plots
# =========================
os.makedirs("figures", exist_ok=True)
fig, axes = plt.subplots(
    nrows=len(irradiance_list),
    ncols=len(workloads),
    figsize=(7, 3.5),
    sharex=False,
    sharey=True
)

irradiance_items = list(irradiance_list.items())

# Outer loop = workloads (columns)
for c, wl in enumerate(workloads):
    for r, (irr_label, irr_value) in enumerate(irradiance_items):
        ax = axes[r, c]
        if wl not in results or irr_label not in results[wl]:
            ax.text(0.5, 0.5, "Missing results", ha="center", va="center")
            ax.grid(True, linestyle='--', alpha=0.6)
            continue

        df = results[wl][irr_label]
        yaxis_label = (c == 0)
        xaxis_label = (r == len(irradiance_list) - 1)
        title_label = (r == 0)
        _plot_rank_panel(ax, df, irr_label, irr_value, wl, yaxis_label=yaxis_label, xaxis_label=xaxis_label, title_label=title_label)

legend_handles = [
    Line2D(
        [0],
        [0],
        color=color,
        lw=2,
        marker=".",
        markersize=6,
        label=device_name_mapping.get(device)
    )
    for device, color in device_colors.items()
]
fig.legend(
    handles=legend_handles,
    frameon=True, 
    loc="upper center",
    fontsize=9,
    ncol=5,
    framealpha=0.8,        # opacity of the frame (0–1)
    edgecolor="black",     # frame border color
    facecolor="white",     # background color of legend box
)

fig.subplots_adjust(right=1, top=0.78, bottom=0, left=0, hspace=0.08, wspace=0.06)
out_path = f"figures/figure6_overall_device_carbon_rank_lifetime{lifetime_years}_solarcap{int(solar_panel_area_cap)}.pdf"
plt.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0)
plt.close(fig)
print(f"📄 Saved figure to {out_path}")
