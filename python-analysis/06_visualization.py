import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys, io, os
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
parquet_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.parquet")
output_dir = os.path.join(script_dir, "..", "charts")
os.makedirs(output_dir, exist_ok=True)

df = pl.read_parquet(parquet_path)
df_clean = df.filter(pl.col("status") != "fault")

plt.rcParams.update({"font.size": 10, "figure.dpi": 120})

# Pre-compute aggregates
stats = df_clean.group_by("equipment_id").agg([
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
    pl.col("vibration").mean().round(2).alias("avg_vibration"),
    pl.col("rpm").mean().round(0).cast(pl.Int64).alias("avg_rpm"),
    pl.col("power_consumption").sum().round(2).alias("total_power"),
]).sort("equipment_id")

eq_labels = [s.replace("-001", "") for s in stats["equipment_id"].to_list()]

# =====================================================
# Chart 1: Temperature time series per equipment
# =====================================================
fig, ax = plt.subplots(figsize=(12, 5))

colors = plt.cm.Set2(np.linspace(0, 1, len(eq_labels)))
equipment_ids = stats["equipment_id"].to_list()
markers = ["o", "s", "D", "^", "v", "<"]

for eq, color, m in zip(equipment_ids, colors, markers):
    eq_df = df_clean.filter(pl.col("equipment_id") == eq).sort("timestamp")
    ax.plot(eq_df["timestamp"], eq_df["temperature"],
            marker=m, linestyle="-", label=eq, color=color,
            markersize=6, linewidth=1.5)

ax.set_xlabel("Time", fontsize=11)
ax.set_ylabel("Temperature (°C)", fontsize=11)
ax.set_title("Monitoring of Industrial Equipment: Temperature Over Time",
             fontsize=13, fontweight="bold")
ax.legend(fontsize=8, ncol=3)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(output_dir, "01_temperature_timeseries.png"))
print(f"Saved: charts/01_temperature_timeseries.png")
plt.close(fig)

# =====================================================
# Chart 2: Multi-panel bar chart — avg metrics
# =====================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

bar_data = [
    (stats["avg_temp"].to_list(), "Avg Temperature (°C)", "#4B8BBE"),
    (stats["avg_pressure"].to_list(), "Avg Pressure", "#306998"),
    (stats["total_power"].to_list(), "Total Power (kW)", "#FFA07A"),
]

for ax, (values, title, color) in zip(axes, bar_data):
    bars = ax.barh(eq_labels, values, height=0.55, color=color, edgecolor="white")
    ax.set_xlabel(title, fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + 0.01 * max(values) + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{v}", va="center", fontsize=8)

fig.tight_layout()
fig.savefig(os.path.join(output_dir, "02_avg_metrics_barh.png"))
print(f"Saved: charts/02_avg_metrics_barh.png")
plt.close(fig)

# =====================================================
# Chart 3: Temperature distribution histogram
# =====================================================
fig, ax = plt.subplots(figsize=(10, 4))

temps = df_clean["temperature"].to_list()
ax.hist(temps, bins=10, edgecolor="white", color="#4B8BBE", alpha=0.85)
mean_val, median_val = np.mean(temps), np.median(temps)
ax.axvline(mean_val, color="red", linestyle="--", linewidth=1.5,
           label=f"Mean: {mean_val:.1f}°C")
ax.axvline(median_val, color="green", linestyle=":", linewidth=1.5,
           label=f"Median: {median_val:.1f}°C")

ax.set_xlabel("Temperature (°C)", fontsize=11)
ax.set_ylabel("Frequency", fontsize=11)
ax.set_title("Temperature Distribution Across All Equipment",
             fontsize=13, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(output_dir, "03_temperature_histogram.png"))
print(f"Saved: charts/03_temperature_histogram.png")
plt.close(fig)

# =====================================================
# Chart 4: Power consumption pie chart
# =====================================================
fig, ax = plt.subplots(figsize=(7, 7))

power = stats.select("equipment_id", "total_power").sort("total_power", descending=True)
pie_labels = [s.replace("-001", "") for s in power["equipment_id"].to_list()]
pie_values = power["total_power"].to_list()
pie_colors = plt.cm.Set3(np.linspace(0, 1, len(pie_labels)))

wedges, texts, autotexts = ax.pie(
    pie_values, labels=pie_labels, autopct="%1.1f%%",
    colors=pie_colors, startangle=90, textprops={"fontsize": 10}
)
ax.set_title("Power Consumption Share by Equipment",
             fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(output_dir, "04_power_pie.png"))
print(f"Saved: charts/04_power_pie.png")
plt.close(fig)

print(f"\nAll charts saved to: {output_dir}")
