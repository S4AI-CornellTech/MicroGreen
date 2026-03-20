import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.lines as mlines
import os, math
import numpy as np
import streamlit as st

##########################################################################################
# location and solar trace mapping
solar_trace_to_location = {
    "solar_5000": "mid_E_72nd",
    "solar_10000": "small_Central_Park_North",
    "solar_50000": "large_Columbus_Circle",
}

##########################################################################################
# Load and clean data
curr_dir = os.path.dirname(os.path.abspath(__file__)) 
csv_path = curr_dir + "/../database/heterogeneous_deployment_simulation_results.csv"

df = pd.read_csv(csv_path)

##########################################################################################
# Knob settings
with st.sidebar:
    deployment_months = st.slider("Deployment Months", min_value=0, max_value=5*12, value=48, step=1)

deployment_days = 30 * deployment_months
##########################################################################################
# trim the df so that we only have data with the right solar irradiance and location
# based on the solar trace to location mapping
filtered_dfs = []
for solar_trace, location in solar_trace_to_location.items():
    temp_df = df[
        (df["solar_trace_max_irradiance"] == solar_trace) &
        (df["visitor_trace_name"] == location) 
        # (df["solar_panel_size_cm2"].isin([0.0, 304.0]))
    ]
    filtered_dfs.append(temp_df)
filtered_dfs = pd.concat(filtered_dfs, ignore_index=True)
print("Filtered df:", filtered_dfs)

##########################################################################################
# calculate total carbon for the deployment days
sweep_rows = []
for idx, row in filtered_dfs.iterrows():
    total_operational = row["battery_grid_carbon_kg"] * deployment_days
    total_carbon = row["total_embodied_carbon_kg"] + total_operational

    sweep_rows.append({
        "solar_panel_size_cm2": row["solar_panel_size_cm2"],
        "visitor_trace_name": row["visitor_trace_name"],
        "solar_trace_max_irradiance": row["solar_trace_max_irradiance"],
        "deployment_day": deployment_days,
        "solar_panel": row["solar_panel_size_cm2"] * 0.0168,
        "board": row["board_carbon"],
        "capacitor": row["capacitor_carbon"],
        "switch": row["capacitor_switch_carbon"],
        "battery_18650": row["battery_18650_carbon_per_2_years"] * math.ceil(deployment_days/730),
        "battery_grid_operational": total_operational,
        "total_carbon_kgCO2e": total_carbon - row["battery_18650_carbon_per_2_years"] + (row["battery_18650_carbon_per_2_years"] * math.ceil(deployment_days/730)),
    })
# Convert to DataFrame
filtered_dfs = pd.DataFrame(sweep_rows)
print("df: ", filtered_dfs)
##########################################################################################
baseline_df = filtered_dfs[filtered_dfs["solar_panel_size_cm2"] == 0]
hybrid_small_solar_panel_df = filtered_dfs[filtered_dfs["solar_panel_size_cm2"] == 74.58]
hybrid_medium_solar_panel_df = filtered_dfs[filtered_dfs["solar_panel_size_cm2"] == 304.0]
hybrid_large_solar_panel_df = filtered_dfs[filtered_dfs["solar_panel_size_cm2"] == 611.0]
solar_only_df = filtered_dfs[~filtered_dfs["solar_panel_size_cm2"].isin([0, 74.58, 304.0, 611.0])]
print("solar only df:", solar_only_df)

# find the row with the largest total carbon in the baseline df
max_baseline_row = baseline_df.loc[baseline_df["total_carbon_kgCO2e"].idxmax()]
max_small_solar_panel_row = hybrid_small_solar_panel_df.loc[hybrid_small_solar_panel_df["total_carbon_kgCO2e"].idxmax()]
max_medium_solar_panel_row = hybrid_medium_solar_panel_df.loc[hybrid_medium_solar_panel_df["total_carbon_kgCO2e"].idxmax()]
max_large_solar_panel_row = hybrid_large_solar_panel_df.loc[hybrid_large_solar_panel_df["total_carbon_kgCO2e"].idxmax()]
max_solar_only_row = solar_only_df.loc[solar_only_df["total_carbon_kgCO2e"].idxmax()]

# construct heterogeneous deployment df by taking row with the smallest total carbon for each location
heterogeneous_deployment_rows = []
for location in solar_trace_to_location.values():
    subset = filtered_dfs[filtered_dfs["visitor_trace_name"] == location]
    min_row = subset.loc[subset["total_carbon_kgCO2e"].idxmin()]
    heterogeneous_deployment_rows.append(min_row)
heterogeneous_deployment_df = pd.DataFrame(heterogeneous_deployment_rows)

##########################################################################################
# Plotting
# x axis are locations
# each location has four bars: baseline, hybrid with one solar panel, hybrid with two solar panels, heterogeneous deployment
locations = list(solar_trace_to_location.values())

def align_to_locations(df, locations):
    return (df.set_index("visitor_trace_name")
              .loc[locations]
              .reset_index())

baseline_df = align_to_locations(baseline_df, locations)
hybrid_small_solar_panel_df  = align_to_locations(hybrid_small_solar_panel_df, locations)
hybrid_medium_solar_panel_df = align_to_locations(hybrid_medium_solar_panel_df, locations)
hybrid_large_solar_panel_df  = align_to_locations(hybrid_large_solar_panel_df, locations)
heterogeneous_deployment_df  = align_to_locations(heterogeneous_deployment_df, locations)

x = np.arange(len(locations))
bar_width = 0.15
fig, ax = plt.subplots(figsize=(10, 7))
# Baseline bars
ax.bar(
    x - 2 * bar_width,
    baseline_df["total_carbon_kgCO2e"],
    width=bar_width,
    label="battery Only",
    color="#E45756"
)
# Hybrid with two solar panels bars
ax.bar(
    x,
    hybrid_medium_solar_panel_df["total_carbon_kgCO2e"],
    width=bar_width,
    label="Hybrid (Medium Solar Panels)",
    color="#54A24B"
)
ax.bar(
    x + 1.0 * bar_width,
    solar_only_df["total_carbon_kgCO2e"],
    width=bar_width,
    label="Solar Harvesting Only",
    color="#72B7B2"
)
# Heterogeneous deployment bars
ax.bar(
    x + 2 * bar_width,
    heterogeneous_deployment_df["total_carbon_kgCO2e"],
    width=bar_width,
    label="Heterogeneous Deployment",
    color="#F58518"
)

ax.set_xticks(x)
ax.set_xticklabels(locations, fontsize=12)
ax.set_ylabel("Total Carbon Footprint (kgCO2e)", fontsize=13)
ax.set_title(f"Total Carbon Footprint over {deployment_days} Days Deployment", fontsize=14)
# put legend at the bottom of the plot
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=11)

st.pyplot(fig)

# plot the aggregate plot for all locations, just four bars
fig2, ax2 = plt.subplots(figsize=(8, 3))
num_locations = len(solar_trace_to_location)
# Baseline bar
columbus_circle_baseline_value = baseline_df[
    baseline_df["visitor_trace_name"] == "large_Columbus_Circle"
]["total_carbon_kgCO2e"].values[0]
ax2.bar(
    0,
    max_baseline_row["total_carbon_kgCO2e"] * num_locations,
    width=0.4,
    label="Baseline (No Solar Panel)",
    color="#E45756"
)
# Hybrid with one solar panel bar
ax2.bar(
    1,
    max_small_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    width=0.4,
    label="Hybrid (small Solar Panel)",
    color="#4C78A8"
)
# Hybrid with two solar panels bar
columbus_circle_medium_value = hybrid_medium_solar_panel_df[
    hybrid_medium_solar_panel_df["visitor_trace_name"] == "large_Columbus_Circle"
]["total_carbon_kgCO2e"].values[0]
ax2.bar(
    2,
    max_medium_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    width=0.4,
    label="Hybrid (medium Solar Panels)",
    color="#54A24B"
)
ax2.bar(
    3,
    max_large_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    width=0.4,
    label="Hybrid (large Solar Panels)",
    color="#72B7B2"
)
ax2.bar(
    4,
    max_solar_only_row["total_carbon_kgCO2e"] * num_locations,
    width=0.4,
    label="solar Harvesting Only",
    color="#72B7B2"
)
# Heterogeneous deployment bar
# get the hetetogeneous deployment balue of columbus circle location
columbus_circle_heterogeneous_value = heterogeneous_deployment_df[
    heterogeneous_deployment_df["visitor_trace_name"] == "large_Columbus_Circle"
]["total_carbon_kgCO2e"].values[0]
ax2.bar(
    5,
    # duplicate the large columbus circle bar for heterogeneous deployment
    heterogeneous_deployment_df["total_carbon_kgCO2e"].sum(),
    width=0.4,
    label="Heterogeneous Deployment",
    color="#F58518"
)
# add the sum value on top of each bar
for i, total in enumerate([
    max_baseline_row["total_carbon_kgCO2e"] * num_locations,
    max_small_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    max_medium_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    max_large_solar_panel_row["total_carbon_kgCO2e"] * num_locations,
    max_solar_only_row["total_carbon_kgCO2e"] * num_locations,
    heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()
]):
    ax2.text(i, total + 0.01 * total, f"{total:.1f}", ha='center', va='bottom', fontsize=10)
# calculate and print the percentage reduction of heterogeneous deployment compared to other deployments
    if i == 3:
        reduction_baseline = (max_baseline_row["total_carbon_kgCO2e"] * num_locations - heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()) / (max_baseline_row["total_carbon_kgCO2e"] * num_locations) * 100
        reduction_hybrid_small = (max_small_solar_panel_row["total_carbon_kgCO2e"] * num_locations - heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()) / (max_small_solar_panel_row["total_carbon_kgCO2e"] * num_locations) * 100
        reduction_hybrid_medium = (max_medium_solar_panel_row["total_carbon_kgCO2e"] * num_locations - heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()) / (max_medium_solar_panel_row["total_carbon_kgCO2e"] * num_locations) * 100
        reduction_hybrid_large = (max_large_solar_panel_row["total_carbon_kgCO2e"] * num_locations - heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()) / (max_large_solar_panel_row["total_carbon_kgCO2e"] * num_locations) * 100
        reduction_solar_only = (max_solar_only_row["total_carbon_kgCO2e"] * num_locations - heterogeneous_deployment_df["total_carbon_kgCO2e"].sum()) / (max_solar_only_row["total_carbon_kgCO2e"] * num_locations) * 100
        print(f"Percentage reduction of heterogeneous deployment compared to baseline: {reduction_baseline:.2f}%")
        print(f"Percentage reduction of heterogeneous deployment compared to hybrid small: {reduction_hybrid_small:.2f}%")
        print(f"Percentage reduction of heterogeneous deployment compared to hybrid medium: {reduction_hybrid_medium:.2f}%")
        print(f"Percentage reduction of heterogeneous deployment compared to hybrid large: {reduction_hybrid_large:.2f}%")
        print(f"Percentage reduction of heterogeneous deployment compared to solar only: {reduction_solar_only:.2f}%")
        st.write(f"- Percentage reduction of heterogeneous deployment compared to battery only: {reduction_baseline:.2f}%")
        st.write(f"- Percentage reduction of heterogeneous deployment compared to hybrid small: {reduction_hybrid_small:.2f}%")
        st.write(f"- Percentage reduction of heterogeneous deployment compared to hybrid medium: {reduction_hybrid_medium:.2f}%")
        st.write(f"- Percentage reduction of heterogeneous deployment compared to hybrid large: {reduction_hybrid_large:.2f}%")
        st.write(f"- Percentage reduction of heterogeneous deployment compared to solar only: {reduction_solar_only:.2f}%")
        
ax2.set_xticks([0, 1, 2, 3, 4, 5])
ax2.set_xticklabels(
    ["battery\nOnly", "Hybrid\n(S Panel)", "Hybrid\n(M Panels)", "Hybrid\n(L Panels)", "solar\nHarvesting\nOnly", "Heterogeneous\nDeployment"],
    fontsize=12
)
ax2.set_ylabel("Total Carbon Footprint (kgCO2e)", fontsize=13)
ax2.set_title(f"Aggregate Total Carbon Footprint over {deployment_days} Days Deployment", fontsize=14)
# put legend at the bottom of the plot
ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=11)
st.pyplot(fig2)

############################################################################################

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
})

# ----- Components and colors -----
components = [
    "solar_panel",
    "board",
    "capacitor",
    "switch",
    "battery_18650",
    "battery_grid_operational",
]

component_labels = {
    "solar_panel": "Solar Panel",
    "board": "Board",
    "capacitor": "Capacitor",
    "switch": "Switches",
    "battery_18650": "Battery (18650)",
    "battery_grid_operational": "Grid Operational",
}

component_colors = {
    "solar_panel": "#4C78A8",             # blue-ish
    "board": "#72B7B2",                   # teal
    "capacitor": "#F58518",               # orange
    "switch": "#E45756",                  # red
    "battery_18650": "#54A24B",           # green
    "battery_grid_operational": "#B279A2" # purple
}

# ----- Deployment configs: DF + label + hatch pattern -----
deployment_configs = [
    ("Battery Only",                 baseline_df,                  ""),    # no hatch
    ("Hybrid (Small Solar Panel)",   hybrid_small_solar_panel_df,  "//"),
    ("Hybrid (Medium Solar Panel)",  hybrid_medium_solar_panel_df, "\\\\"),
    ("Hybrid (Large Solar Panel)",   hybrid_large_solar_panel_df,  "xx"),
    ("solar harvesting Only",          solar_only_df,                "++"),
    ("Heterogeneous Deployment",     heterogeneous_deployment_df,  ".."),
]

# x axis are locations
locations = list(solar_trace_to_location.values())
x = np.arange(len(locations))
bar_width = 0.15

fig3, ax = plt.subplots(figsize=(10, 9))

# ----- Plot stacked bars for each deployment type -----
# We assume each deployment_*_df has rows in the same order as `locations`.
center_index = (len(deployment_configs) - 1) / 2.0

for i, (deploy_label, deploy_df, hatch_pattern) in enumerate(deployment_configs):
    # x-offset for this deployment
    offset = (i - center_index) * bar_width
    x_pos = x + offset

    # bottom starts at zero for stacking
    bottom = np.zeros(len(locations))

    for comp in components:
        values = deploy_df[comp].values
        print(f"Plotting {comp} for {deploy_label}: values={values}, bottom={bottom}")

        bars = ax.bar(
            x_pos,
            values,
            width=bar_width,
            bottom=bottom,
            color=component_colors[comp],
            edgecolor="black",
            hatch=hatch_pattern
        )

        # update bottom for next component in the stack
        bottom += values

# ----- Axes labels, ticks, title -----
ax.set_xticks(x)
ax.set_xticklabels(locations, fontsize=12, rotation=0)
ax.set_ylabel("Total Carbon Footprint (kgCO$_2$e)", fontsize=13)
ax.set_title(f"Stacked Carbon Footprint Components over {deployment_days} Days", fontsize=14)

# ----- Legends: one for components (color), one for deployment type (hatch) -----
# Component legend (colors)
component_handles = [
    Patch(facecolor=component_colors[c], edgecolor="black", label=component_labels[c])
    for c in components
]

# Deployment legend (hatches)
deployment_handles = [
    Patch(facecolor="white", edgecolor="black", hatch=h, label=label)
    for (label, _, h) in deployment_configs
]

# First legend: components (place at bottom center)
legend1 = ax.legend(
    handles=component_handles,
    loc="upper left",
    bbox_to_anchor=(0.5, -0.18),
    ncol=3,
    fontsize=9,
    title="Components"
)

# Second legend: deployment types (place below the first)
legend2 = ax.legend(
    handles=deployment_handles,
    loc="upper right",
    bbox_to_anchor=(0.5, -0.32),
    ncol=2,
    fontsize=9,
    title="Deployment Type"
)

# Add the first legend back to the axes
ax.add_artist(legend1)

ax.set_ylim(0, ax.get_ylim()[1] * 1.1)  # add some space on top for clarity

plt.tight_layout(rect=[0, 0.2, 1, 1])
st.pyplot(fig3)


# plot fig2 and fig3 side by side using streamlit
st.write("### Aggregate Comparison")
col1, col2 = st.columns(2)
with col1:
    st.pyplot(fig2)
with col2:
    st.pyplot(fig3)

##########################################################################################

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

# ===============================================================
# Data already computed in your workflow
# ---------------------------------------------------------------
deployment_labels = [
    "Battery Only",
    "Hybrid (S Panel)",
    "Hybrid (M Panel)",
    "Hybrid (L Panel)",
    "Solar Only",
    "Heterogeneous",
]

aggregate_totals = [
    max_baseline_row["total_carbon_kgCO2e"] * len(solar_trace_to_location),
    max_small_solar_panel_row["total_carbon_kgCO2e"] * len(solar_trace_to_location),
    max_medium_solar_panel_row["total_carbon_kgCO2e"] * len(solar_trace_to_location),
    max_large_solar_panel_row["total_carbon_kgCO2e"] * len(solar_trace_to_location),
    max_solar_only_row["total_carbon_kgCO2e"] * len(solar_trace_to_location),
    heterogeneous_deployment_df["total_carbon_kgCO2e"].sum(),
]

bar_hashes = [
    "",
    "//",
    "\\\\",
    "xx",
    "++",
    "..",
]

# ===============================================================
#    CREATE ONE FIGURE: Bar + Pie Charts (for 3 locations)
# ---------------------------------------------------------------

locations_order = [
    "large_Columbus_Circle",
    "mid_E_72nd",
    "small_Central_Park_North"
]

location_titles = {
    "large_Columbus_Circle": "Columbus Circle",
    "mid_E_72nd": "E 72nd St",
    "small_Central_Park_North": "Central Park North",
}

fig = plt.figure(figsize=(3.5, 3))
gs = fig.add_gridspec(2, 6, height_ratios=[1, 1.5], width_ratios=[1.9, 1, 1.9, 1, 1.9, 1])

# -------------------------
# TOP: Horizontal Bar Chart
# -------------------------
ax_bar = fig.add_subplot(gs[0, 1:])

y_pos = np.arange(len(deployment_labels))
ax_bar.barh(y_pos, aggregate_totals, hatch=bar_hashes, edgecolor="black", color="white")
ax_bar.set_yticks(y_pos)
ax_bar.set_yticklabels(deployment_labels, fontsize=10)
ax_bar.invert_yaxis()  # largest at top
ax_bar.set_xlabel("Total Carbon Footprint (kg CO$_2$e)", fontsize=11, labelpad=0)
ax_bar.set_xlim(0, max(aggregate_totals) * 1.2)
ax_bar.tick_params(axis='both', pad=-1)

# Add labels at bar ends
for i, total in enumerate(aggregate_totals):
    ax_bar.text(total * 1.01, i, f"{total:.1f}", va="center", fontsize=9)

# # Helper to decide deployment type label for this row
def get_deployment_type(row):
    panel_area = row["solar_panel_size_cm2"]
    has_batt = row["battery_18650"] > 0
    has_panel = row["solar_panel"] > 0

    if has_batt and not has_panel:
        return "Battery Only"
    if has_batt and has_panel:
        # Hybrid, choose size label by area
        if np.isclose(panel_area, 74.58):
            return "Hybrid (Small Panel)"
        elif np.isclose(panel_area, 304.0):
            return "Hybrid (Medium Panel)"
        elif np.isclose(panel_area, 611.0):
            return "Hybrid (Large Panel)"
        else:
            return "Hybrid Deployment"
    if not has_batt and has_panel:
        return "Solar Harvesting Only"
    return "Other Deployment"

axes_pie = [fig.add_subplot(gs[1, 0:1]), fig.add_subplot(gs[1, 2:3]), fig.add_subplot(gs[1, 4:5])]

def autopct_if_big(pct):
    return f"{pct:.0f}%" if pct >= 10 else ""

for ax_pie, loc in zip(axes_pie, locations_order):
    row = heterogeneous_deployment_df[
        heterogeneous_deployment_df["visitor_trace_name"] == loc
    ].iloc[0]

    values = [row[c] for c in components]
    labels = [component_labels[c] for c in components]
    colors = [component_colors[c] for c in components]

    v2, l2, c2 = [], [], []
    for v, lab, col in zip(values, labels, colors):
        if v > 0:
            v2.append(v)
            l2.append(lab)
            c2.append(col)

    wedges, texts, autotexts = ax_pie.pie(
        v2,
        labels=None,
        autopct=autopct_if_big,
        pctdistance=0.72,
        colors=c2,
        startangle=90,
        radius=2.5,  # 1.0 is fine now that the axes are larger
        wedgeprops={"edgecolor": "white", "linewidth": 0.5},
    )
    ax_pie.set_aspect("equal", "box")

    for t in autotexts:
        t.set_fontsize(8)

    deploy_type = get_deployment_type(row)
    ax_pie.set_title(f"{location_titles[loc]}\n{deploy_type}", fontsize=9, pad=25)
# -------------------------
# Global Legend for Pie Components
# -------------------------
component_handles = [
    Patch(facecolor=component_colors[c], edgecolor="black", label=component_labels[c])
    for c in components
]

fig.legend(
    handles=component_handles,
    loc="lower center",
    ncol=3,
    fontsize=8,
    bbox_to_anchor=(0.5, -0.02),
    frameon=False
)

fig.subplots_adjust(hspace=0.5, wspace=0.35, left=0.1, right=0.99, top=0.99, bottom=0.1)
fig.savefig(curr_dir + f"/../figures/figure13_heterogeneous_deployment.pdf", dpi=300)