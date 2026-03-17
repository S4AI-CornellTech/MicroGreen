import numpy as np
from matplotlib.lines import Line2D
from constants import * 
from helper import *

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
})

def lifetime_plot(lifetime_workload_df_solar, lifetime_workload_df_battery, lifetime_workload_df_hybrid):
    max_lifetime_years = 3
    # max_lifetime_years = 0.15
    lifetime_years = np.arange(0, max_lifetime_years, 0.005)  # integer years for clarity

    fig_life, axes = plt.subplots(1, 3, figsize=(3.5, 2), sharex=True, sharey=True)

    # Solar-powered: total carbon is constant (embodied carbon only)

    for _, row in lifetime_workload_df_solar.iterrows():
        total_carbon = row["total embodied carbon (kg CO2e)"]
        axes[0].plot(lifetime_years, [total_carbon] * len(lifetime_years), label=f"{row['Devices']} (solar)", linestyle=":", color=device_colors[row['Devices']])
        axes[0].tick_params(axis='both', pad=0)
        axes[0].set_title("Solar\nharvesting only  ", pad=3, fontsize=9)
 
    # Battery-powered: carbon increases with battery usage over time
    for _, row in lifetime_workload_df_battery.iterrows():
        board_carbon = row["board embodied carbon (kg CO2e)"]
        battery_carbon_per_year = row["battery carbon per year (kg CO2e)"]
        total_carbon_over_time = board_carbon + battery_carbon_per_year * lifetime_years
        axes[1].plot(lifetime_years, total_carbon_over_time, label=f"{row['Devices']} (battery)", linestyle="-", color=device_colors[row['Devices']])
        axes[1].tick_params(axis='both', pad=0)
        axes[1].set_title("Battery-\npowered only", pad=3, fontsize=9)
    # Hybrid-powered: carbon increases with battery usage over time, but at a reduced rate
    for _, row in lifetime_workload_df_hybrid.iterrows():
        embodied_carbon = row["total embodied carbon (kg CO2e)"]
        battery_carbon_per_year = row["hybrid battery carbon over lifetime (kg CO2e)"]
        total_carbon_over_time = embodied_carbon + battery_carbon_per_year * lifetime_years
        axes[2].plot(lifetime_years, total_carbon_over_time, label=f"{row['Devices']} (hybrid)", linestyle="-.", color=device_colors[row['Devices']])
        axes[2].tick_params(axis='both', pad=0)
        devices = lifetime_workload_df_solar["Devices"].unique().tolist()
        axes[2].set_title("Hybrid", pad=3, fontsize=9)

    axes[0].set_xticks([0,1,2,3])
    axes[1].set_xlabel("Deployment Lifetime (years)", labelpad=0)
    axes[0].set_ylabel("Cumulative Carbon\nEmissions (kg CO$_2$e)", labelpad=0)
    axes[0].set_yscale("log")

    style_map = {
        "Solar harvesting only": ":",
        "Battery-powered only": "-",
        "Hybrid": "-.",
    }

    curated_device_colors = {device: device_colors[device] for device in devices}

    device_name_mapping["nxprt1176+TPU"] = "NXP RT1176\n+ TPU"

    handles = [
        Line2D(
            [0],
            [0],
            color=color,
            lw=2,
            marker=".",
            markersize=6,
            label=device_name_mapping.get(device)
        )
        for device, color in curated_device_colors.items()      
    ]

    # Create a legend
    fig_life.legend(
        handles=handles, 
        frameon=False, 
        loc="upper center", 
        ncol=4, 
        bbox_to_anchor=(0.5, 1.03),
        fontsize=8,
        labelspacing=0.2, # vertical space between legend entries
        columnspacing=0.4, # horizontal space between legend columns
        handletextpad=0.2 # space between legend marker and text
    )

    fig_life.subplots_adjust(left=0.15, right=0.99, top=0.75, bottom=0.15, wspace=0.1)
    fig_life.savefig("figures/Mobisys_lifetime_plot.pdf", dpi=300)