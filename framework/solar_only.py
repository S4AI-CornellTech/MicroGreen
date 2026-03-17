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
        * 2
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

    # fig, ax = plt.subplots(figsize=(5, 3))
    fig, ax = plt.subplots(figsize=(1.6, 3))

    components = [
        "kg CO2e (capacitor only)",
        "kg CO2e (solar panel)",
        "kg CO2e (board)",
        "kg CO2e (voltage regulator)",
        "kg CO2e (switches only)"
    ]
    colors = map_components_to_colors(components)

    # only show rp2040, rp2350, nf52840 in the plot
    # workload_df_solar = workload_df_solar[
    #     workload_df_solar["Devices"].isin(["rp2040", "rp2350", "nf52840"])
    # ]

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
    ax.set_title(f"Embodied Carbon for {workload} with Solar Harvesting")
    ax.set_xticklabels(workload_df_solar["Devices"], rotation=20)
    ax.legend(
        ["Capacitor", "Solar Panel", "Board", "Voltage Regulator", "Switches"],
        bbox_to_anchor=(1.05, 1), loc='upper left'
    )
    st.markdown(
        "**Note:** The percentages on top of each bar indicate the _duty cycle_ — "
        "the proportion of time a device is actively performing inference, including required charging time."
    )
    st.pyplot(fig)
    fig.savefig("figures/solar_harvesting_embodied_carbon.pdf", dpi=300)

    # ===============================
    # Cost Stacked Bar Chart Plot  (solar harvesting)
    # ===============================

    st.subheader(f"Monetary Cost for {workload} (Solar Harvesting Mode)")

    fig, ax = plt.subplots(figsize=(3.6, 3))
    # fig, ax = plt.subplots(figsize=(5, 3))

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
    ax.set_title(f"Embodied Carbon for {workload} with Solar Harvesting")
    ax.set_xticklabels(workload_df_solar["Devices"], rotation=20)
    ax.legend(
        ["Capacitor", "Solar Panel", "Board", "Voltage Regulator", "Switches"],
        bbox_to_anchor=(1.05, 1), loc='upper left'
    )
    plt.tight_layout()
    st.markdown(
        "**Note:** The percentages on top of each bar indicate the _duty cycle_ — "
        "the proportion of time a device is actively performing inference, including required charging time."
    )
    st.pyplot(fig)
    if GENERATE_PLOTS:
        fig.savefig("figures/solar_harvesting_cost.pdf", dpi=300)

    # ===============================
    # embodied carbon over irradiance plot
    # ===============================
    irradiance_levels = np.arange(10, 2000, 10)  # from 100 to 2000 uW/cm²

    fig_irr, ax_irr = plt.subplots(figsize=(5, 2.8))

    # Plot the embodied carbon for each device at different irradiance levels
    for device in workload_df_solar["Devices"].unique():

        device_df = workload_df_solar[workload_df_solar["Devices"] == device]
        embodied_carbon = []

        for irr in irradiance_levels:
            area_cm2 = calculate_solar_panel_area(
                device_df["inference energy (mJ)"].values[0],
                irradiance=irr,
                inference_per_second=inference_per_second
            )
            carbon = area_cm2 * solar_panel_emission_per_cm2

            embodied_carbon.append(
                carbon
                + device_df["kg CO2e (board)"].values[0]
                + device_df["kg CO2e (voltage regulator)"].values[0]
                + device_df["kg CO2e (capacitor only)"].values[0]
                + device_df["kg CO2e (switches only)"].values[0]
            )

        ax_irr.plot(
            irradiance_levels, embodied_carbon,
            label=device, color=device_colors[device]
        )

    ax_irr.set_xlabel("Irradiance (uW/cm²)", fontsize=11)
    ax_irr.set_ylabel("Embodied Carbon (kg CO2e)", fontsize=11)
    ax_irr.set_xscale("log")
    ax_irr.set_yscale("log")

    ax_irr.axvline(x=50, color='red', linestyle='--')
    ax_irr.axvline(x=1500, color='red', linestyle='--')
    ax_irr.text(18, 1.3, 'Low Light\nIndoor',
                rotation=0, verticalalignment='center',
                color='red', fontsize=10)
    ax_irr.text(450, 1, 'Bright Light\nOutdoor',
                rotation=0, verticalalignment='center',
                color='red', fontsize=10)

    ax_irr.set_title(
        f"Embodied Carbon vs. Irradiance for {workload} (Solar Harvesting Mode)"
    )
    ax_irr.legend(ncol=2, fontsize=10)
    ax_irr.grid(True)

    # ===============================
    # embodied carbon over inference per sec plot
    # ===============================
    inference_per_sec_levels = np.arange(0.1, 30, 0.1)

    fig_inf, ax_inf = plt.subplots(figsize=(6, 4))

    for device in workload_df_solar["Devices"].unique():
        device_df = workload_df_solar[workload_df_solar["Devices"] == device]
        embodied_carbon = []

        for inf_per_sec in inference_per_sec_levels:
            area_cm2 = calculate_solar_panel_area(
                device_df["inference energy (mJ)"].values[0],
                inference_per_second=inf_per_sec,
                irradiance=irradiance
            )
            carbon = area_cm2 * solar_panel_emission_per_cm2

            embodied_carbon.append(
                carbon
                + device_df["kg CO2e (board)"].values[0]
                + device_df["kg CO2e (voltage regulator)"].values[0]
                + device_df["kg CO2e (capacitor only)"].values[0]
                + device_df["kg CO2e (switches only)"].values[0]
            )

        ax_inf.plot(
            inference_per_sec_levels, embodied_carbon,
            label=device, color=device_colors[device]
        )

    ax_inf.set_xlabel("Inferences Per Second")
    ax_inf.set_ylabel("Embodied Carbon (kg CO2e)")
    ax_inf.set_title(
        f"Embodied Carbon vs. Inferences Per Second for {workload} (Solar Harvesting Mode)"
    )
    ax_inf.legend(ncol=2)
    ax_inf.grid(True)

    col1, col2 = st.columns(2)
    with col1:
        st.pyplot(fig_irr)
        if GENERATE_PLOTS:
            fig_irr.savefig(
                "figures/solar_harvesting_embodied_carbon_vs_irradiance.pdf",
                dpi=300
            )
    with col2:
        st.pyplot(fig_inf)
        if GENERATE_PLOTS:
            fig_inf.savefig(
                "figures/solar_harvesting_embodied_carbon_vs_inference_per_second.pdf",
                dpi=300
            )

    # ===============================
    # Total Embodied Carbon vs Inference Energy
    # ===============================
    st.subheader(f"Total Embodied Carbon vs Inference Energy ({workload})")

    fig_ce, ax_ce = plt.subplots(figsize=(3.2, 3))

    for device in workload_df_solar["Devices"].unique():
        device_df = workload_df_solar[workload_df_solar["Devices"] == device]

        x_energy = device_df["inference energy (mJ)"].values[0]
        y_carbon = device_df["total embodied carbon (kg CO2e)"].values[0]

        ax_ce.scatter(
            x_energy,
            y_carbon,
            color=device_colors.get(device, "black"),
            label=device
        )

        # Small label next to each point
        label_carbon = f"{y_carbon:.3f} kg"
        label_energy = f"{x_energy:.3f} mJ"
        ax_ce.text(
            x_energy,
            y_carbon,
            device + " " + label_carbon + ", " + label_energy,
            fontsize=8,
            ha="left",
            va="bottom",
            rotation=25,
        )

    ax_ce.set_xlabel("Inference Energy per Inference (mJ)")
    ax_ce.set_ylabel("Total Embodied Carbon (kg CO2e)")
    ax_ce.set_title(
        f"Total Embodied Carbon vs Inference Energy\n{workload}, {irradiance} μW/cm², {inference_per_second} IPS"
    )

    # Avoid duplicate legend labels by building once from unique devices
    handles, labels = ax_ce.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))

    ax_ce.grid(True, which="both", linestyle="--", linewidth=0.5)

    plt.tight_layout()
    st.pyplot(fig_ce)
    if GENERATE_PLOTS:
        fig_ce.savefig(
            "figures/solar_harvesting_total_carbon_vs_inference_energy.pdf",
            dpi=300,
        )
