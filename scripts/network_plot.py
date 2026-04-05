import polars as pl
import altair as alt
from io import StringIO

# CONSTANTS
VOLTAGE = 3.3
CO2_PER_BATTERY_KG = 0.107
ENERGY_PER_BATTERY_J = 11250
kg_co2_per_joule = CO2_PER_BATTERY_KG / ENERGY_PER_BATTERY_J
WIFI_CONNECTION_TIME_S = 8

LIFETIME_YEARS = 2
INFERENCES_PER_MINUTE = 10
BATCH_INTERVAL_MINUTES = 10
RESULT_BYTES = 4

inferences_per_batch = INFERENCES_PER_MINUTE * BATCH_INTERVAL_MINUTES
batches_per_lifetime = (LIFETIME_YEARS * 365 * 24 * 60) / BATCH_INTERVAL_MINUTES

# Raw measurement data
csv_data = """device,metric,value,unit
RP2040,BLE_transmission_current,36.475,mA
RP2350,BLE_transmission_current,13.813,mA
ESP32,BLE_transmission_current,78.047,mA
nRF52840,BLE_transmission_current,7.63,mA
RP2040,idle_current,13.409,mA
RP2350,idle_current,6.881,mA
ESP32,idle_current,46.593,mA
nRF52840,idle_current,3.231,mA
RP2040,BLE_throughput,57.8,kbps
RP2350,BLE_throughput,58.0,kbps
ESP32,BLE_throughput,54.3,kbps
nRF52840,BLE_throughput,58.1,kbps
"""

wifi_antenna_idle = pl.DataFrame({
    "device": ["RP2040", "RP2350", "ESP32"],
    "antenna_idle_wifi_mA": [79.418, 74.202, 85.818],
}).with_columns(
    (pl.col("antenna_idle_wifi_mA") * VOLTAGE * WIFI_CONNECTION_TIME_S).alias("wifi_connection_energy_mJ"),
    ((pl.col("antenna_idle_wifi_mA") * VOLTAGE * WIFI_CONNECTION_TIME_S / 1000) * kg_co2_per_joule).alias("wifi_connection_carbon_kgco2"),
)

model_sizes = pl.DataFrame({
    "Model": ["kws-s", "kws-l", "ppd-s", "ppd-l"],
    "input_bytes": [40 * 49, 40 * 49, 96 * 96 * 1, 96 * 96 * 3],
})

# Parse and pivot transmission data
df = pl.read_csv(StringIO(csv_data))
df = df.with_columns([
    pl.when(pl.col("metric").str.contains("BLE")).then(pl.lit("BLE"))
      .when(pl.col("metric").str.contains("WIFI")).then(pl.lit("WiFi"))
      .otherwise(pl.lit("Both")).alias("protocol"),
])

transmission_df = (
    df.filter(pl.col("metric").str.contains("transmission_current|throughput"))
    .filter(pl.col("protocol") != "Both")
    .with_columns(
        pl.when(pl.col("metric").str.contains("current"))
          .then(pl.lit("current_mA"))
          .otherwise(pl.lit("throughput_kbps"))
          .alias("metric_clean")
    )
    .pivot(index=["device", "protocol"], on="metric_clean", values="value")
)

energy_per_byte = pl.col("current_mA") * VOLTAGE * 8 / (pl.col("throughput_kbps") * 1000)
transmission_df = transmission_df.with_columns(
    energy_per_byte.alias("transmission_energy_per_byte_mJ"),
    (energy_per_byte / 1000 * kg_co2_per_joule).alias("transmission_carbon_per_byte_kgco2"),
)

device_map = {
    "rp2040": "RP2040",
    "rp2350": "RP2350",
    "esp32": "ESP32",
    "nf52840": "nRF52840",
}

inf_df = (
    pl.read_csv("database/profiling_results.csv")
    .select(["Devices", "Model", "Total Processing Time (us)", "inference energy (mJ)"])
    .rename({"Devices": "device"})
    .filter(pl.col("device").is_in(device_map.keys()))
    .with_columns(pl.col("device").replace(device_map))
    .with_columns(
        ((pl.col("inference energy (mJ)") / 1000) * kg_co2_per_joule).alias("inference_carbon_kgco2")
    )
)

combined_df = inf_df.join(model_sizes, on="Model").join(transmission_df, on="device")

scatter_df = (
    combined_df.select([
        "device", "protocol", "Model", "input_bytes",
        "inference energy (mJ)", "inference_carbon_kgco2",
        "transmission_energy_per_byte_mJ", "transmission_carbon_per_byte_kgco2",
    ])
    .join(wifi_antenna_idle, on="device", how="left")
    .with_columns([
        (pl.col("inference energy (mJ)") * batches_per_lifetime * inferences_per_batch).alias("lifetime_inference_energy_mJ"),
        (pl.col("inference_carbon_kgco2") * batches_per_lifetime * inferences_per_batch).alias("lifetime_inference_carbon_kgco2"),
        (
            (batches_per_lifetime * inferences_per_batch * RESULT_BYTES * pl.col("transmission_energy_per_byte_mJ"))
            + pl.when(pl.col("protocol") == "WiFi").then(pl.col("wifi_connection_energy_mJ") * batches_per_lifetime).otherwise(0.0)
        ).alias("lifetime_label_transmission_energy_mJ"),
        (
            (batches_per_lifetime * inferences_per_batch * RESULT_BYTES * pl.col("transmission_carbon_per_byte_kgco2"))
            + pl.when(pl.col("protocol") == "WiFi").then(pl.col("wifi_connection_carbon_kgco2") * batches_per_lifetime).otherwise(0.0)
        ).alias("lifetime_label_transmission_carbon_kgco2"),
        (
            (batches_per_lifetime * inferences_per_batch * pl.col("input_bytes") * pl.col("transmission_energy_per_byte_mJ"))
            + pl.when(pl.col("protocol") == "WiFi").then(pl.col("wifi_connection_energy_mJ") * batches_per_lifetime).otherwise(0.0)
        ).alias("lifetime_raw_transmission_energy_mJ"),
        (
            (batches_per_lifetime * inferences_per_batch * pl.col("input_bytes") * pl.col("transmission_carbon_per_byte_kgco2"))
            + pl.when(pl.col("protocol") == "WiFi").then(pl.col("wifi_connection_carbon_kgco2") * batches_per_lifetime).otherwise(0.0)
        ).alias("lifetime_raw_transmission_carbon_kgco2"),
    ])
)

# Build and save the crossover plot
plot_df = (
    scatter_df.filter((pl.col("Model") == "ppd-s") & (pl.col("protocol") == "BLE"))
    .select([
        "device",
        (pl.col("lifetime_inference_carbon_kgco2") + pl.col("lifetime_label_transmission_carbon_kgco2")).alias("Local Inference"),
        pl.col("lifetime_raw_transmission_carbon_kgco2").alias("Offload Raw Data"),
    ])
    .unpivot(
        index=["device"],
        on=["Local Inference", "Offload Raw Data"],
        variable_name="strategy",
        value_name="carbon_kgco2",
    )
)

device_order = (
    scatter_df.filter((pl.col("Model") == "ppd-s") & (pl.col("protocol") == "BLE"))
    .with_columns(
        (pl.col("lifetime_inference_carbon_kgco2") + pl.col("lifetime_label_transmission_carbon_kgco2")).alias("local_total")
    )
    .sort("local_total")
    .select("device")
    .to_series()
    .to_list()
)

bar_chart = (
    alt.Chart(plot_df.to_pandas())
    .mark_bar()
    .encode(
        y=alt.Y("device:N", sort=device_order, title=None, axis=alt.Axis(labelAngle=0)),
        x=alt.X("carbon_kgco2:Q", title="Lifetime Carbon Emissions (kg CO₂)"),
        color=alt.Color(
            "strategy:N",
            title=None,
            scale=alt.Scale(
                domain=["Local Inference", "Offload Raw Data"],
                range=["#525252", "#ff6b6b"],
            ),
            legend=alt.Legend(
                orient="none", legendX=160, legendY=5,
                direction="vertical", fillColor="white",
                strokeColor="lightgray", padding=5,
            ),
        ),
        yOffset=alt.YOffset("strategy:N"),
        tooltip=["device:N", "strategy:N", "carbon_kgco2:Q"],
    )
    .properties(width=280, height=150)
    .configure(font="Times New Roman")
    .configure_axis(labelFontSize=12, titleFontSize=13)
    .configure_legend(labelFontSize=12, titleFontSize=13)
)

bar_chart.save("figures/figure9_networking_crossover_plot.pdf")