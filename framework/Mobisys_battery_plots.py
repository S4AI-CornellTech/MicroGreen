import numpy as np
from matplotlib.lines import Line2D
from matplotlib import gridspec

from constants import * 
from helper import *

low_ips = 0.1
high_ips = 10

# TODO: ips = 0.1 and IPS = 10 text


plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
})

def battery_plot(low_ips_workload_df_battery, high_ips_workload_df_battery):
    fig_battery= plt.figure(figsize=(3.5, 2))

    gs_carbon = gridspec.GridSpec(nrows=1, ncols=2, width_ratios=[1,1])
    gs_cost = gridspec.GridSpec(nrows=1, ncols=2, width_ratios=[1,1])

    ax_low_ips_carbon  = fig_battery.add_subplot(gs_carbon[0, 0])
    ax_high_ips_carbon = fig_battery.add_subplot(gs_carbon[0, 1])
    ax_low_ips_cost   = fig_battery.add_subplot(gs_cost[0, 0])
    ax_high_ips_cost  = fig_battery.add_subplot(gs_cost[0, 1])

    gs_carbon.update(left = 0.08, right = 0.48, wspace = 0.26)
    gs_cost.update(left = 0.57, right = 0.99, wspace = 0.26)

    # ===============================
    # Stacked multi-bar Chart Plot CO2 (battery powered) low IPS
    # ===============================

    components = [
        "board embodied carbon (kg CO2e)",
        "battery carbon over lifetime (kg CO2e)"
    ]

    colors = map_components_to_colors(components)

    low_ips_workload_df_battery = low_ips_workload_df_battery[
        low_ips_workload_df_battery["Devices"].isin(["esp32S3", "rp2350", "nxprt1176+TPU"])
    ]

    low_ips_workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_low_ips_carbon, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    low_ips_workload_df_battery = low_ips_workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in low_ips_workload_df_battery.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        # duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * low_ips * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            # f"{duty_cycle:.1f}%",              # duty cycle
            # f"{total_height:.1f}kg",  # total embodied carbon
            f"{batteries_per_day:.3f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax_low_ips_carbon.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=8, rotation=45
        )

    # Final plot polish
    ymin, ymax = ax_low_ips_carbon.get_ylim()
    ax_low_ips_carbon.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax_low_ips_carbon.set_ylabel("Embodied Carbon (kg CO2e)", labelpad=0)
    ax_low_ips_carbon.set_xticklabels(["ESP32-S3", "RP2350", "NXP RT1176\n  +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_low_ips_carbon.set_yticklabels([f"{int(tick)}" for tick in ax_low_ips_carbon.get_yticks()], rotation=90, va='center')
    ax_low_ips_carbon.tick_params(axis='both', pad=-1)

    ax_low_ips_carbon.set_facecolor('RoyalBlue')
    ax_low_ips_carbon.patch.set_alpha(0.3)

    ax_low_ips_carbon.text(
        0.35, 0.95, 'IPS\n0.1',
        transform=ax_low_ips_carbon.transAxes,
        fontsize=8,
        verticalalignment='top',
        color='RoyalBlue'
    )

    curated_component_colors = {
        component: component_colors[component]
        for component in ['board', 'battery']
    }

    handles = [
        Line2D(
            [0],
            [0],
            color=color,
            lw=8,
            label=component
        )
        for component, color in curated_component_colors.items()
    ]

    ax_low_ips_carbon.legend(
        handles=handles,
        loc='upper center',
        bbox_to_anchor=(2.5, 1.18),
        ncol=2,
        fontsize=9,
        frameon=False
    )

    # ===============================
    # Stacked multi-bar Chart Plot CO2 (battery powered) high IPS
    # ===============================

    components = [
        "board embodied carbon (kg CO2e)",
        "battery carbon over lifetime (kg CO2e)"
    ]

    colors = map_components_to_colors(components)

    high_ips_workload_df_battery = high_ips_workload_df_battery[
        high_ips_workload_df_battery["Devices"].isin(["esp32S3", "rp2350", "nxprt1176+TPU"])
    ]

    high_ips_workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_high_ips_carbon, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    high_ips_workload_df_battery = high_ips_workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in high_ips_workload_df_battery.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        # duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * high_ips * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            # f"{duty_cycle:.1f}%",              # duty cycle
            # f"{total_height:.1f}kg",  # total embodied carbon
            f"{batteries_per_day:.3f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax_high_ips_carbon.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=8, rotation=45
        )

    # Final plot polish
    ymin, ymax = ax_high_ips_carbon.get_ylim()
    ax_high_ips_carbon.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax_high_ips_carbon.set_xticklabels(["ESP32-S3", "RP2350", "NXP RT1176\n  +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_high_ips_carbon.set_yticklabels([f"{int(tick)}" for tick in ax_high_ips_carbon.get_yticks()], rotation=90, va='center')
    ax_high_ips_carbon.tick_params(axis='both', pad=-1)
    ax_high_ips_carbon.legend().set_visible(False)

    ax_high_ips_carbon.set_facecolor('red')
    ax_high_ips_carbon.patch.set_alpha(0.3)

    ax_high_ips_carbon.text(
        0.6, 0.95, 'IPS\n10',
        transform=ax_high_ips_carbon.transAxes,
        fontsize=8,
        verticalalignment='top',
        color='red'
    )

    # ===============================
    # Stacked multi-bar Chart Plot Cost (battery powered) low ips
    # ===============================

    components = [
        "board cost ($)",
        "battery cost ($)"
    ]              

    colors = map_components_to_colors(components)

    # only show esp32S3 rp2350 nxp devices
    low_ips_workload_df_battery = low_ips_workload_df_battery[
        low_ips_workload_df_battery["Devices"].isin(["esp32S3", "rp2350", "nxprt1176+TPU"])
    ]

    low_ips_workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_low_ips_cost, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    low_ips_workload_df_battery_reset = low_ips_workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in low_ips_workload_df_battery_reset.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * low_ips * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            # f"${total_height:.0f}",  # total cost
            # f"{duty_cycle:.1f}%",              # duty cycle
            # f"{total_height:.0f}kg",  # total embodied carbon
            # f"{batteries_per_day:.2f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax_low_ips_cost.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )

    # Final plot polish
    ax_low_ips_cost.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax_low_ips_cost.set_ylabel("Monetary Cost ($)", labelpad=0)
    ax_low_ips_cost.set_xticklabels(["ESP32-S3", "RP2350", "NXP RT1176\n  +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_low_ips_cost.set_yticklabels([f"{int(tick)}" for tick in ax_low_ips_cost.get_yticks()], rotation=90)
    ax_low_ips_cost.legend().set_visible(False)
    ax_low_ips_cost.tick_params(axis='both', pad=-1)

    ax_low_ips_cost.set_facecolor('RoyalBlue')
    ax_low_ips_cost.patch.set_alpha(0.3)

    ax_low_ips_cost.text(
        0.1, 0.95, 'IPS\n0.1',
        transform=ax_low_ips_cost.transAxes,
        fontsize=8,
        verticalalignment='top',
        color='RoyalBlue'
    )

    # ===============================
    # Stacked multi-bar Chart Plot Cost (battery powered) high ips
    # ===============================

    components = [
        "board cost ($)",
        "battery cost ($)"
    ]              

    colors = map_components_to_colors(components)

    # only show esp32S3 rp2350 nxp devices
    high_ips_workload_df_battery = high_ips_workload_df_battery[
        high_ips_workload_df_battery["Devices"].isin(["esp32S3", "rp2350", "nxprt1176+TPU"])
    ]

    high_ips_workload_df_battery.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_high_ips_cost, color=colors, width=0.8
    )

    # add labels on top of bars: Duty cycle, number of batteries per day
    pad = 0.01  # vertical padding above the bar (in y-axis units)
    high_ips_workload_df_battery = high_ips_workload_df_battery.reset_index(drop=True)
    total_heights_list = []
    for i, row in high_ips_workload_df_battery.iterrows():
        total_height = row[components].sum()
        total_heights_list.append(total_height)
        duty_cycle = row["battery duty cycle (%)"]
        batteries_per_day = row["batteries per inference"] * low_ips * 60 * 60 * 24

        # Build a multi-line label
        label_lines = [
            # f"${total_height:.0f}",  # total cost
            # f"{duty_cycle:.1f}%",              # duty cycle
            # f"{total_height:.0f}kg",  # total embodied carbon
            # f"{batteries_per_day:.2f}" # batteries per day
            # f"{batteries_per_day:.2f} AA battery/day" # batteries per day
        ]
        label = "\n".join(label_lines)

        ax_high_ips_cost.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9, fontweight='bold'
        )

    ax_high_ips_cost.set_facecolor('red')
    ax_high_ips_cost.patch.set_alpha(0.3)

    ax_high_ips_cost.text(
        0.6, 0.95, 'IPS\n10',
        transform=ax_high_ips_cost.transAxes,
        fontsize=8,
        verticalalignment='top',
        color='red'
    )

    # Final plot polish
    ax_high_ips_cost.set_ylim(ymin, max(total_heights_list) * 1.25)
    ax_high_ips_cost.set_xticklabels(["ESP32-S3", "RP2350", "NXP RT1176\n  +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_high_ips_cost.set_yticklabels([f"{int(tick)}" for tick in ax_high_ips_cost.get_yticks()], rotation=90)
    ax_high_ips_cost.legend().set_visible(False)
    ax_high_ips_cost.tick_params(axis='both', pad=-1)
    
    fig_battery.subplots_adjust(left=0.08, right=0.99, top=0.9, bottom=0.2, wspace=0.25)
    fig_battery.savefig("figures/Mobisys_battery_plot.pdf", dpi=300)
