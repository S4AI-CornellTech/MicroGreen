import numpy as np
from matplotlib.lines import Line2D
from matplotlib import gridspec

inference_per_second = 1
workload = "kws-l"
lifetime_years = 3

from constants import * 
from helper import *

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
})

def solar_plot(indoor_workload_df_solar, outdoor_workload_df_solar):
    # ===============================
    # embodied carbon over irradiance plot
    # ===============================
    irradiance_levels = np.arange(10, 90000, 10)  # from 100 to 2000 uW/cm²

    fig_irr= plt.figure(figsize=(3.5, 2.5))

    gs = gridspec.GridSpec(nrows=1, ncols=3, width_ratios=[2, 1, 1])

    ax_irr  = fig_irr.add_subplot(gs[0, 0])
    ax_low  = fig_irr.add_subplot(gs[0, 1])
    ax_high = fig_irr.add_subplot(gs[0, 2])

    # Plot the embodied carbon for each device at different irradiance levels
    for device in indoor_workload_df_solar["Devices"].unique():

        device_df = indoor_workload_df_solar[indoor_workload_df_solar["Devices"] == device]
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

    ax_irr.set_xscale("log")
    ax_irr.set_yscale("log")

    ax_irr.axvline(x=50, color='RoyalBlue', linestyle='--')
    ax_irr.axvline(x=60000, color='red', linestyle='--')
    ax_irr.text(60, 350, 'Low Light\nIndoor',
                rotation=0, verticalalignment='center',
                color='RoyalBlue', fontsize=10)
    ax_irr.text(50000, 50, 'Bright Light\nOutdoor',
                rotation=0, verticalalignment='center',
                color='red', fontsize=10, ha='right')

    ax_irr.grid(True)
    # get rid of tick labels
    # ax_irr.set_xticklabels([])
    # ax_irr.set_yticklabels([])
    ax_irr.tick_params(axis='both', pad=0)
    ax_irr.set_xlabel("Irradiance (uW/cm²)", fontsize=11, labelpad=0)
    ax_irr.set_ylabel("Embodied Carbon (kg CO2e)", fontsize=11, labelpad=0)

    #############################################################################
    # legend
    devices = indoor_workload_df_solar["Devices"].unique()
    curated_device_colors = {device: device_colors[device] for device in devices}

    # change NXP to "nxp52840" in the legend
    device_name_mapping["nxprt1176+TPU"] = "NXP RT1176\n+ TPU"

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
        for device, color in curated_device_colors.items()      
    ]
    
    fig_irr.legend(
        handles=legend_handles,
        frameon=False, 
        loc="upper center",
        fontsize=8,
        ncol=2,
        framealpha=0.8,        # opacity of the frame (0–1)
        facecolor="white",     # background color of legend box
        bbox_to_anchor=(0.23, 1.04),
        labelspacing=0.2, # vertical space between legend entries
        columnspacing=0.4, # horizontal space between legend columns
        handletextpad=0.2 # space between legend marker and text
    )

    # ===============================
    # Carbon Emission Stacked Bar Chart Plot (solar harvesting)
    # ===============================

    components = [
        "kg CO2e (capacitor only)",
        "kg CO2e (solar panel)",
        "kg CO2e (board)",
        "kg CO2e (voltage regulator)",
        "kg CO2e (switches only)"
    ]
    colors = map_components_to_colors(components)

    # only show rp2040, rp2350, nxprt1176+TPU, nf52840
    indoor_workload_df_solar = indoor_workload_df_solar[
        indoor_workload_df_solar["Devices"].isin(["rp2040", "rp2350", "nxprt1176+TPU"])
    ]

    print("indoor_workload_df_solar:\n", indoor_workload_df_solar)
    indoor_workload_df_solar.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_low, color=colors, width=0.7
    )

    pad = 0.01  
    indoor_workload_df_solar_reset = indoor_workload_df_solar.reset_index(drop=True)

    for i, row in indoor_workload_df_solar_reset.iterrows():
        total_height = row[components].sum()
        area_cm2 = row["solar panel area (cm2)"]
        caps = (
            row.get("number of capacitors", None)
            * row.get("number of capacitor sets", 1)
            * lifetime_years
            * 12
        )

        # Build a multi-line label
        label_lines = [
            # f"{total_height:.2f} kg",  
            # f"{duty_cycle:.1f}%",              
            f"{area_cm2:.0f}",             
            # f"{area_cm2/10000:.2f} m²",             
            # f"{int(caps)} caps" if caps is not None else ""  
        ]
        label = "\n".join([s for s in label_lines if s])

        ax_low.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9,
        )

    ymin, ymax = ax_low.get_ylim()
    ax_low.set_ylim(ymin, ymax * 1.25)

    ax_low.set_xticklabels(["RP2040", "RP2350", "NXP RT1176\n    +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_low.tick_params(axis='both', pad=0)

    curated_component_colors = {
        component: component_colors[component]
        for component in ['capacitor', 'solar panel', 'board', 'switch', 'voltage regulator']
    }

    # make the background color royalblue
    ax_low.set_facecolor('RoyalBlue')
    ax_low.patch.set_alpha(0.3)
    # add text in the top left corner
    ax_low.text(
        0.35, 0.98, 'Indoor',
        transform=ax_low.transAxes,
        fontsize=10,
        verticalalignment='top',
        color='RoyalBlue'
    )

    # build legend based on component colors
    handles = [
        Line2D(
            [0],
            [0],
            color=color,
            lw=8,
            label=component if component != 'voltage regulator' else 'voltage\nregulator'
        )
        for component, color in curated_component_colors.items()
    ]
    ax_low.legend(
        handles=handles,
        frameon=False, 
        loc="upper right",
        fontsize=9,
        framealpha=0.8,        # opacity of the frame (0–1)
        facecolor="white",     # background color of legend box
        bbox_to_anchor=(2.6, 1.36),
        labelspacing=0.3, # vertical space between legend entries
        columnspacing=0.8, # horizontal space between legend columns
        handletextpad=0.8, # space between legend marker and text
        ncol=2,
        borderpad=0.7,      # increase inner padding
    )

    # ===============================
    # Carbon Emission Stacked Bar Chart Plot (solar harvesting) bright light
    # ===============================

    components = [
        "kg CO2e (capacitor only)",
        "kg CO2e (solar panel)",
        "kg CO2e (board)",
        "kg CO2e (voltage regulator)",
        "kg CO2e (switches only)"
    ]
    colors = map_components_to_colors(components)

    # only show rp2040, rp2350, nxprt1176+TPU, nf52840
    outdoor_workload_df_solar = outdoor_workload_df_solar[
        outdoor_workload_df_solar["Devices"].isin(["rp2040", "rp2350", "nxprt1176+TPU"])
    ]

    print("outdoor_workload_df_solar:\n", outdoor_workload_df_solar)
    outdoor_workload_df_solar.set_index("Devices")[components].plot(
        kind='bar', stacked=True, ax=ax_high, color=colors, width=0.7
    )

    pad = 0.01  
    outdoor_workload_df_solar_reset = outdoor_workload_df_solar.reset_index(drop=True)

    for i, row in outdoor_workload_df_solar_reset.iterrows():
        total_height = row[components].sum()
        area_cm2 = row["solar panel area (cm2)"]
        caps = (
            row.get("number of capacitors", None)
            * row.get("number of capacitor sets", 1)
            * lifetime_years
            * 12
        )

        # Build a multi-line label
        label_lines = [
            # f"{total_height:.2f} kg",  
            # f"{duty_cycle:.1f}%",              
            f"{area_cm2:.1f}",             
            # f"{area_cm2/10000:.2f} m²",             
            # f"{int(caps)} caps" if caps is not None else ""  
        ]
        label = "\n".join([s for s in label_lines if s])

        ax_high.text(
            i, total_height + pad,
            label,
            ha='center', va='bottom', fontsize=9,
        )

    ymin, ymax = ax_high.get_ylim()
    ax_high.set_ylim(ymin, ymax * 1.25)

    ax_high.set_xticklabels(["RP2040", "RP2350", "NXP RT1176\n    +TPU"], rotation=30, fontsize=8, rotation_mode='anchor', ha='right')
    ax_high.tick_params(axis='both', pad=0)

    # make no legend for the high light plot
    ax_high.legend().set_visible(False)

    # make the background color red
    ax_high.set_facecolor('red')
    ax_high.patch.set_alpha(0.3)
    # add text in the top left corner
    ax_high.text(
        0.25, 0.98, 'Outdoor',
        transform=ax_high.transAxes,
        fontsize=10,
        verticalalignment='top',
        color='red'
    )

    fig_irr.subplots_adjust(left=0.11, right=0.99, top=0.82, bottom=0.17, wspace=0.25)
    fig_irr.savefig("figures/Figure7_Mobisys_irradiance_plot.pdf", dpi=300)