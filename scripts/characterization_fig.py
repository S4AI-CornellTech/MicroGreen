import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os,sys
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from framework.constants import * 

device_name_mapping = {
    "esp32": "ESP32",
    "esp32C6": "ESP32-C6",
    "esp32S3": "ESP32-S3",
    "nf52840": "nRF52840",
    "rp2040": "RP2040",
    "rp2350": "RP2350",
    "stm32f411fe": "STM32F4",
    "nxprt1176+TPU": "NXP RT1176\n+TPU",
    "nxprt1176": "NXP RT1176",
} 

# =========================
# Unified font configuration
# =========================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

##########################################################################################
# Load dataset
curr_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
csv_path = "database/profiling_results.csv"  # Update path as needed
df = pd.read_csv(csv_path)

trimmed_df = df.dropna(subset=[
    "inference energy (mJ)",
    "Total Processing Time (us)",
])

##########################################################################################

workloads = ["kws-s", "kws-l", "ppd-s", "ppd-l", "pd-MobileNetV2", "pd-YOLOv8"]  # enforce a consistent order

devices_sorted_low_to_high = sorted(whole_board_carbon, key=whole_board_carbon.get)

# sort device_name_mapping according to devices_sorted_low_to_high
sorted_device_names = [device_name_mapping[dev] for dev in devices_sorted_low_to_high]
# change nxprt1176+TPU to "NXP RT1176 + TPU"
sorted_device_names = [name.replace("NXP RT1176 + TPU", "NXP RT1176\n+TPU") for name in sorted_device_names]

bar_width = 0.8
bar_with_special = 0.6
# fig, axs = plt.subplots(2, 6, figsize=(7, 2.7), sharex=False, sharey='row')
fig = plt.figure(figsize=(7, 2.7))
gs = fig.add_gridspec(
    2, 6,
    hspace=0.1,
    wspace=0.1,
    width_ratios=[1, 1, 1, 1, 0.25, 0.25],
)

axs = gs.subplots(sharey='row', sharex=False)

# make the first row subplot barplot with processing time (y axis) per device (x axis)

for col, wl in enumerate(workloads):
    wl_df = trimmed_df[trimmed_df["Model"] == wl]
    if wl ==  "pd-MobileNetV2":
        title_name = "MbV2"
    elif wl == "pd-YOLOv8":
        title_name = "YOLO"
    elif wl == "kws-s":
        title_name = "KWS-S"
    elif wl == "kws-l":
        title_name = "KWS-L"
    elif wl == "ppd-s":
        title_name = "PPD-S"
    elif wl == "ppd-l":
        title_name = "PPD-L"
    else:
        title_name = wl
    axs[0, col].set_title(title_name, pad=0)

    plotted_devices = []

    for device in devices_sorted_low_to_high:
        dev_df = wl_df[wl_df["Devices"] == device]

        # Skip if this device has no data for the workload
        if dev_df.empty:
            continue

        color = device_colors.get(device, "black")

        # Take the scalar value in ms
        y_ms = dev_df["Total Processing Time (us)"].iloc[0] / 1000.0

        # Use integer x positions instead of the string name
        x_pos = len(plotted_devices)
        axs[0, col].bar(
            x_pos,
            y_ms,
            color=color,
            width = bar_width if wl != "pd-MobileNetV2" and wl != "pd-YOLOv8" else bar_with_special,
        )
        plotted_devices.append(device)

    # remove xtick labels for the first row
    axs[0, col].set_xticks([])
    axs[0, col].set_xticklabels([])

# Axes labels per row (only leftmost column to avoid clutter)
axs[0, 0].set_ylabel("Processing\nTime (ms)", labelpad=0)

# Log scale on y for all subplots in first row
for c in range(6):
    axs[0, c].tick_params(axis='both', pad=0)
    axs[0, c].set_yscale("log")
    axs[0, c].grid(True, which="both", ls="--", linewidth=0.5)

# second row: scatter plot of inference energy for each device per workload
for col, wl in enumerate(workloads):
    wl_df = trimmed_df[trimmed_df["Model"] == wl]

    plotted_devices = []

    for device in devices_sorted_low_to_high:
        dev_df = wl_df[wl_df["Devices"] == device]

        # Skip if this device has no data for the workload
        if dev_df.empty:
            continue

        color = device_colors.get(device, "black")

        # Take the scalar value in mJ
        y_ms = dev_df["inference energy (mJ)"].iloc[0]

        # Use integer x positions instead of the string name
        x_pos = len(plotted_devices)
        axs[1, col].bar(
            x_pos,
            y_ms,
            color=color,
            width = bar_width if wl != "pd-MobileNetV2" and wl != "pd-YOLOv8" else bar_with_special,
        )
        plotted_devices.append(device)

    print(f"Workload: {wl}, Plotted devices: {plotted_devices}")
    plotted_device_names = [device_name_mapping[dev] for dev in plotted_devices]
    axs[1, col].set_xticks(range(len(plotted_devices)))
    axs[1, col].set_xticklabels(plotted_device_names, rotation=90, ha="center", fontsize=8)
    for label in axs[1, col].get_xticklabels():
        label.set_linespacing(0.8)

# Axes labels per row (only leftmost column to avoid clutter)
axs[1, 0].set_ylabel("Inference\nEnergy (mJ)", labelpad=0)

# Log scale on y for all subplots in second row
for c in range(6):
    axs[1, c].set_yscale("log")
    axs[1, c].tick_params(axis='both', pad=0)
    axs[1, c].grid(True, which="both", ls="--", linewidth=0.5)

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

fig.subplots_adjust(left=0.07, right=0.99, top=0.95, bottom=0.24, hspace=0.02, wspace=0.15)
os.makedirs(os.path.join(curr_dir, "figures"), exist_ok=True)
plt.savefig(os.path.join(curr_dir, "figures", "per_inference_runtime_energy.pdf"), dpi=300)