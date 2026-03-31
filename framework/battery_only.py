import streamlit as st
import numpy as np

from constants import * 
from helper import *

def run_battery_powered_analysis(
    workload_df,
    workload,
    inference_per_second,
    lifetime_years,
):
    # calculate duty cycle for battery powered mode
    workload_df["battery duty cycle (%)"] = (
        (workload_df["Total Processing Time (us)"] / 1e6) * inference_per_second
    ) * 100 

    workload_df_battery = workload_df[workload_df["battery duty cycle (%)"] <= 100].copy()

    # Calculate the number of AA batteries needed per inference
    workload_df_battery["batteries per inference"] = workload_df_battery["inference energy (mJ)"] / 1000 / AA_energy

    # Calculate the embodied carbon for batteries
    workload_df_battery["battery carbon (kg CO2e)"] = workload_df_battery["batteries per inference"] * AA_carbon

    # Calculate the total embodied carbon for batteries per year
    workload_df_battery["battery carbon per year (kg CO2e)"] = workload_df_battery["battery carbon (kg CO2e)"] * 365 * inference_per_second * 60 * 60 * 24

    # Calculate the total embodied carbon over the deployment lifetime
    workload_df_battery["battery carbon over lifetime (kg CO2e)"] = workload_df_battery["battery carbon per year (kg CO2e)"] * lifetime_years

    # Calculate the total embodied carbon for the board
    workload_df_battery["board embodied carbon (kg CO2e)"] = workload_df["Devices"].map(whole_board_carbon)

    # Calculate total carbon emissions
    workload_df_battery["total embodied carbon (kg CO2e)"] = (
        workload_df_battery["board embodied carbon (kg CO2e)"]
        + workload_df_battery["battery carbon over lifetime (kg CO2e)"]
    )

    # calculate monetary cost for battery powered mode
    workload_df_battery["battery cost ($)"] = workload_df_battery["batteries per inference"] * AA_battery_cost * 365 * inference_per_second * 60 * 60 * 24 * lifetime_years
    workload_df_battery["board cost ($)"] = workload_df_battery["Devices"].map(monetary_cost)

    workload_df_battery["total monetary cost ($)"] = (
        workload_df_battery["board cost ($)"]
        + workload_df_battery["battery cost ($)"]
    )

    return workload_df_battery

def battery_analysis_plots(workload_df_battery, workload, inference_per_second, lifetime_years):
    # ===============================
    # Stacked multi-bar Chart Plot CO2 (battery powered)
    # ===============================
    st.subheader(f"Embodied Carbon for {workload} (Battery Powered Mode)")

    fig, ax = plt.subplots(figsize=(4.5, 3))

    components = [
        "board embodied carbon (kg CO2e)",
        "battery carbon over lifetime (kg CO2e)"
    ]

    colors = map_components_to_colors(components)

    # workload_df_battery = workload_df_battery[
    #     workload_df_battery["Devices"].isin(["esp32S3", "rp2350", "nxprt1176+TPU"])
    # ]

    workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    workload_df_battery_reset = workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in workload_df_battery_reset.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * inference_per_second * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            # f"{duty_cycle:.1f}%",              # duty cycle
            f"{total_height:.1f}kg",  # total embodied carbon
            f"{batteries_per_day:.3f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )

    # Final plot polish
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax.set_ylabel("Embodied Carbon (kg CO2e)")
    ax.set_xticklabels(workload_df_battery["Devices"], rotation=20, fontsize=10, weight='bold')
    ax.set_yticklabels([f"{tick}" for tick in ax.get_yticks()], rotation=90, va='center')
    # ax.legend(["Board", "Battery"], bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.legend(["Board", "Battery"], bbox_to_anchor=(1.1, 1), loc='upper left')
    plt.tight_layout()
    
    st.markdown(
        "**Note:** Number of AA batteries needed per day is marked on top of the bar along with the total embodied carbon of the system."
    )
    
    st.pyplot(fig)
    if GENERATE_PLOTS:
        fig.savefig("figures/battery_powered_embodied_carbon.pdf", dpi=300)

    # ===============================
    # Stacked multi-bar Chart Plot Cost (battery powered)
    # ===============================
    st.subheader(f"Monetary Cost for {workload} (Battery Powered Mode)")

    fig, ax = plt.subplots(figsize=(4.5, 3))

    components = [
        "board cost ($)",
        "battery cost ($)"
    ]              

    colors = map_components_to_colors(components)


    workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    workload_df_battery_reset = workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in workload_df_battery_reset.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * inference_per_second * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            f"${total_height:.0f}",  # total cost
            # f"{duty_cycle:.1f}%",              # duty cycle
            # f"{total_height:.0f}kg",  # total embodied carbon
            # f"{batteries_per_day:.2f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )

    # Final plot polish
    ax.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax.set_ylabel("Monetary Cost ($)")
    ax.set_xticklabels(workload_df_battery["Devices"], rotation=20, fontsize=10, weight='bold')
    ax.set_yticklabels([f"{int(tick)}" for tick in ax.get_yticks()], rotation=90, va='center')
    ax.legend(["Board", "Battery"], bbox_to_anchor=(1.1, 1), loc='upper left')
    plt.tight_layout()

    st.pyplot(fig)
    if GENERATE_PLOTS:
        fig.savefig("figures/battery_powered_cost.pdf", dpi=300)