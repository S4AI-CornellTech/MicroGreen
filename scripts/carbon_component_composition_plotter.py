import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# =========================
# Unified font configuration
# =========================

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
})

# -----------------------------
# Load CSV
# -----------------------------
curr_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
csv_filename = "/database/board_carbon.csv"

df = pd.read_csv(curr_dir + csv_filename)

# -----------------------------
# Preprocess
# -----------------------------
df = df.rename(columns={df.columns[0]: "Board"})

# Drop Total column
if "Total" in df.columns:
    df = df.drop(columns=["Total"])

# Rename board labels
df["Board"] = df["Board"].replace({
    "coralDevMicro": "Coral Dev\nMicro",
    "nRF52840": "nRF  \n52840",
    "STM32F411": "STM32\nF411FE",
})

df.set_index("Board", inplace=True)
df = df.fillna(0)

# Normalize rows to percentage
df_pct = df.div(df.sum(axis=1), axis=0) * 100

components = df_pct.columns.tolist()

# Colors
cmap = plt.cm.tab20
colors = {comp: cmap(i+3) for i, comp in enumerate(components)}

# -----------------------------
# Plot Horizontal
# -----------------------------
fig, ax = plt.subplots(figsize=(3.5, 2.6))

y = np.arange(len(df_pct))
bar_height = 0.6

left = np.zeros(len(df_pct))

for comp in components:
    values = df_pct[comp].values
    
    # Draw bar segment
    ax.barh(
        y,
        values,
        left=left,
        height=bar_height,
        label=comp,
        color=colors[comp],
        edgecolor="white",
        linewidth=0.4
    )
    
    # Add text label if >10%
    for i, val in enumerate(values):
        if val > 10:
            ax.text(
                left[i] + val / 2,   # center within the segment
                y[i],
                f"{val:.1f}%",
                va="center",
                ha="center",
                color="black"
            )
    
    left += values

# -----------------------------
# Formatting
# -----------------------------
ax.set_xlabel("Percentage of Total Carbon Contribution (%)", labelpad=0)
ax.set_yticks(y)
ax.set_yticklabels(df_pct.index)
ax.set_xlim(0, 100)

ax.legend(
    ncol=3,
    bbox_to_anchor=(0.42, 1.42),
    loc="upper center",
    frameon=True,
    fontsize=9
)

plt.subplots_adjust(left=0.19, right = 0.97, top=0.75, bottom=0.14)
plt.savefig(curr_dir + "/figures/figure3_board_carbon_composition_stacked_bar.pdf", dpi=300)
