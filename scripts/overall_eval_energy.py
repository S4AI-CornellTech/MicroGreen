# energy_rank_plot.py
import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from framework.constants import device_colors, device_name_mapping

# =========================
# setup
# =========================
workloads = ["kws-s", "kws-l", "ppd-s", "ppd-l"]
inferece_per_second_map = {
    "kws-s": np.arange(0.1, 15.0, 0.01),
    "kws-l": np.arange(0.1, 15.0, 0.01),
    "ppd-s": np.arange(0.1, 15.0, 0.1),
    "ppd-l": np.arange(0.1, 30.0, 0.1),
}

# =========================
# load + preprocess
# =========================
curr_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."
csv_path = os.path.join(curr_dir, "database/profiling_results.csv")
df = pd.read_csv(csv_path)

df = df.dropna(subset=[
    "inference energy (mJ)",
    "Total Processing Time (us)",
    "Devices",
    "Model",
])

df["Model"] = df["Model"].astype(str).str.strip().str.lower()
df["Total Processing Time (us)"] = (
    df["Total Processing Time (us)"].astype(str).str.replace(",", "", regex=False)
)
df["Total Processing Time (us)"] = pd.to_numeric(df["Total Processing Time (us)"], errors="coerce")

required_cols = ["Devices", "Model", "inference energy (mJ)", "Total Processing Time (us)"]
df = df[required_cols].dropna()

workload_df_map = {
    wl: df.loc[df["Model"] == wl, required_cols].copy()
    for wl in workloads
}

# =========================
# compute energy rank
# =========================
def compute_energy_rank_df(wdf: pd.DataFrame, ips_list: np.ndarray) -> pd.DataFrame:
    devices = wdf["Devices"].tolist()
    out = pd.DataFrame(index=devices, columns=ips_list, dtype=float)

    proc_s = wdf["Total Processing Time (us)"].to_numpy(dtype=float) * 1e-6
    e_mj = wdf["inference energy (mJ)"].to_numpy(dtype=float)

    for ips in ips_list:
        feasible = (ips * proc_s) <= 1.0
        e_per_sec = np.where(feasible, e_mj * ips, np.nan)
        out[ips] = e_per_sec

    return out.rank(axis=0, method="min", ascending=True)

energy_rank_results = {}
for wl in workloads:
    wdf = workload_df_map[wl]
    ips_list = inferece_per_second_map[wl]
    energy_rank_results[wl] = compute_energy_rank_df(wdf, ips_list)

# =========================
# plot
# =========================
os.makedirs("figures", exist_ok=True)

fig, axes = plt.subplots(
    nrows=1,
    ncols=len(workloads),
    figsize=(7, 1.6),
    sharey=True,
    sharex=False
)

if len(workloads) == 1:
    axes = [axes]

for c, wl in enumerate(workloads):
    ax = axes[c]
    rank_df = energy_rank_results[wl]

    ips = pd.to_numeric(rank_df.columns, errors="coerce").to_numpy(dtype=float)
    n_devices = len(rank_df.index)

    for device in rank_df.index:
        y = rank_df.loc[device].to_numpy(dtype=float)
        if np.all(np.isnan(y)):
            continue
        ax.plot(
            ips,
            y,
            marker='.',
            linewidth=0.8,
            markersize=0.8,
            color=device_colors.get(device, "gray")
        )

    ax.set_title(wl.upper(), fontsize=10)
    ax.set_xlabel("IPS", fontsize=9, labelpad=0)
    ax.set_yticks([1, 2, 3, 4, 5, 6, 7, 8, 9])
    ax.tick_params(axis='both', which='major', pad=0)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_ylim(n_devices + 0.5, 0.5)

axes[0].set_ylabel("Rank (1 = lowest\nenergy nper inference)", fontsize=9, labelpad=0.05)

# =========================
# unified legend
# =========================
legend_handles = [
    Line2D(
        [0],
        [0],
        color=color,
        lw=2,
        marker=".",
        markersize=6,
        label=device_name_mapping.get(device, device)
    )
    for device, color in device_colors.items()
]

fig.legend(
    handles=legend_handles,
    loc="upper center",
    ncol=5,
    frameon=True,
    fontsize=9,
    framealpha=0.8,
    edgecolor="black"
)

fig.subplots_adjust(top=0.55, wspace=0.05, bottom=0, left=0.01, right=1)

out_path = "figures/energy_optimal_device_rank_vs_ips.pdf"
plt.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0)
plt.close(fig)

print(f"saved: {out_path}")
