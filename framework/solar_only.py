import streamlit as st
import numpy as np

from constants import * 
from helper import *

def run_solar_harvesting_analysis(
    workload_df,
    workload,
    irradiance,
    inference_per_second,
    lifetime_years,
):
    """
    Compute solar-harvesting metrics, embodied carbon, monetary cost,
    and generate all plots. All original commented-out code is preserved.
    """

    # ==========================================
    # Dataframe Calculations
    # ==========================================

    # Calculate the energy stored in capacitors (in Joules)
    workload_df["energy in capacitors (mJ)"] = workload_df.apply(
        lambda row: calculate_energy_in_capacitors(
            row["number of capacitors"], row["Vh"], row["Vl"]
        ),
        axis=1
    )

    # calculate solar panel area required for inference frequency
    workload_df["solar panel area (cm2)"] = workload_df["inference energy (mJ)"].apply(
        lambda x: calculate_solar_panel_area(
            x, irradiance=irradiance, inference_per_second=inference_per_second
        )
    )

    # calculate the charging time per inference
    workload_df["charging time per inference (s)"] = workload_df.apply(
        lambda row: calculate_charging_time_per_inference(
            row["energy in capacitors (mJ)"],
            row["solar panel area (cm2)"],
            irradiance=irradiance
        ),
        axis=1
    ).copy()

    # need to calculate the number of cpacitor sets needed for each processor to achieve zero charging time
    workload_df["number of capacitor sets"] = (
        workload_df["Total Processing Time (us)"] * 1e-6
        / workload_df["charging time per inference (s)"]
        + 1
    )

    workload_df["solar duty cycle (%)"] = (
        (workload_df["Total Processing Time (us)"] / 1e6) * inference_per_second
    ) * 100 


    # if the duty cycle is larger than 100%, take the device off the dataframe
    # form a new dataframe with devices that can run the workload, named `workload_df_solar`
    # workload_df_solar = workload_df.copy()
    print("workload-df:\n", workload_df)
    workload_df_solar = workload_df[workload_df["solar duty cycle (%)"] <= 100].copy()

    # calculate different compoenent's embodied carbon
    workload_df_solar["kg CO2e (solar panel)"] = (
        workload_df_solar["solar panel area (cm2)"] * solar_panel_emission_per_cm2
    )
    workload_df_solar["kg CO2e (board)"] = workload_df_solar["Devices"].map(
        whole_board_carbon
    )
    workload_df_solar["kg CO2e (voltage regulator)"] = workload_df_solar["Devices"].map(
        voltage_regulator_CO2
    )
    workload_df_solar["kg CO2e (capacitor only)"] = (
        workload_df_solar["kg CO2e (capacitor only)"]
        * workload_df_solar["number of capacitor sets"]
        * lifetime_years
        * 12
    )
    workload_df_solar["kg CO2e (switches only)"] = capacitor_switches_CO2e * (
        workload_df_solar["number of capacitor sets"] - 1
    )

    workload_df_solar["total embodied carbon (kg CO2e)"] = (
        workload_df_solar["kg CO2e (capacitor only)"]
        + workload_df_solar["kg CO2e (solar panel)"]
        + workload_df_solar["kg CO2e (board)"]
        + workload_df_solar["kg CO2e (voltage regulator)"]
        + workload_df_solar["kg CO2e (switches only)"]
    )

    # calculate monetary cost for solar harvesting mode
    workload_df_solar["solar panel cost ($)"] = (
        workload_df_solar["solar panel area (cm2)"] * solar_panel_per_cm2_cost
    )
    workload_df_solar["capacitor cost ($)"] = (
        workload_df_solar["number of capacitors"]
        * per_capacitor_cost
        * workload_df_solar["number of capacitor sets"]
        * 2 # we need to have two sets of capcitors to support "non-stop" inference, so we multiply by 2 to get the total number of capacitors used in the system.
    )
    workload_df_solar["voltage regulator cost ($)"] = workload_df_solar["Devices"].map(
        voltage_regulator_cost
    )
    workload_df_solar["board cost ($)"] = workload_df_solar["Devices"].map(
        monetary_cost
    )
    workload_df_solar["switch cost ($)"] = capacitor_switches_cost * (
        workload_df_solar["number of capacitor sets"] - 1
    )

    workload_df_solar["total monetary cost ($)"] = (
        workload_df_solar["solar panel cost ($)"]
        + workload_df_solar["capacitor cost ($)"]
        + workload_df_solar["voltage regulator cost ($)"]
        + workload_df_solar["board cost ($)"]
        + workload_df_solar["switch cost ($)"]
    )

    return workload_df_solar

def solar_analysis_plots(workload_df_solar, workload, inference_per_second, irradiance, lifetime_years):

    # ===============================
    # Carbon Emission Stacked Bar Chart Plot (solar harvesting)
    # ===============================

    st.subheader(f"Embodied Carbon for {workload} (Solar Harvesting Mode)")

    fig, ax = plt.subplots(figsize=(5, 3))

    components = [
        "kg CO2e (capacitor only)",
        "kg CO2e (solar panel)",
        "kg CO2e (board)",
        "kg CO2e (voltage regulator)",
        "kg CO2e (switches only)"
    ]
    colors = map_components_to_colors(components)

    print("workload_df_solar:\n", workload_df_solar)
    workload_df_solar.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax, color=colors, width=0.7
    )

    pad = 0.01  
    workload_df_solar_reset = workload_df_solar.reset_index(drop=True)

    for i, row in workload_df_solar_reset.iterrows():
        total_height = row[components].sum()
        duty_cycle = row["solar duty cycle (%)"]
        area_cm2 = row["solar panel area (cm2)"]
        caps = (
            row.get("number of capacitors", None)
            * row.get("number of capacitor sets", 1)
            * lifetime_years
            * 12
        )

        # Build a multi-line label
        label_lines = [
            f"{total_height:.2f} kg",  
            # f"{duty_cycle:.1f}%",              
            f"{area_cm2:.0f} cm²",             
            # f"{area_cm2/10000:.2f} m²",             
            # f"{int(caps)} caps" if caps is not None else ""  
        ]
        label = "\n".join([s for s in label_lines if s])

        ax.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9,
        )

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax * 1.25)

    ax.set_ylabel("Embodied Carbon (kg CO2e)")
    ax.set_xticklabels(workload_df_solar["Devices"], rotation=20)
    ax.legend(
        ["Capacitor", "Solar Panel", "Board", "Voltage Regulator", "Switches"],
        bbox_to_anchor=(0.5, 1.2), loc='upper center', ncol=5
    )
    st.markdown(
        "**Note:** The area of the solar panel needed is marked on top of the bar along with the total embodied carbon of the system."
    )
    st.pyplot(fig)
    fig.savefig("figures/solar_harvesting_embodied_carbon.pdf", dpi=300)

    # ===============================
    # Cost Stacked Bar Chart Plot  (solar harvesting)
    # ===============================

    st.subheader(f"Monetary Cost for {workload} (Solar Harvesting Mode)")

    fig, ax = plt.subplots(figsize=(5, 3))

    components = [
        "capacitor cost ($)",
        "solar panel cost ($)",
        "board cost ($)",
        "voltage regulator cost ($)",
        "switch cost ($)"
    ]
    colors = map_components_to_colors(components)

    print("workload_df_solar:\n", workload_df_solar)
    workload_df_solar.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax, color=colors, width=0.7
    )

    pad = 0.01  
    workload_df_solar_reset = workload_df_solar.reset_index(drop=True)

    for i, row in workload_df_solar_reset.iterrows():
        total_height = row[components].sum()
        duty_cycle = row["solar duty cycle (%)"]
        area_cm2 = row["solar panel area (cm2)"]
        caps = (
            row.get("number of capacitors", None)
            * row.get("number of capacitor sets", 1)
            * lifetime_years
            * 12
        )

        # Build a multi-line label
        label_lines = [
            f"${total_height:.1f}",  
            # f"{duty_cycle:.1f}%",              
            # f"{area_cm2/10000:.2f} m²",             
            # f"{int(caps)} caps" if caps is not None else ""  
        ]
        label = "\n".join([s for s in label_lines if s])

        ax.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9,
        )

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax * 1.25)

    ax.set_ylabel("Monetary Cost ($)")
    ax.set_xticklabels(workload_df_solar["Devices"], rotation=20)
    ax.legend(
        ["Capacitor", "Solar Panel", "Board", "Voltage Regulator", "Switches"],
        bbox_to_anchor=(0.5, 1.2), loc='upper center', ncol=5, fontsize=9
    )
    plt.tight_layout()
    st.pyplot(fig)
    if GENERATE_PLOTS:
        fig.savefig("figures/solar_harvesting_cost.pdf", dpi=300)