import polars as pl
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.jsonl")

df = pl.read_ndjson(file_path)
df = df.with_columns(pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%.f%:z"))
df_clean = df.filter(pl.col("status") != "fault")

# ---------------------------------------------------------------------------
# 1. Aggregation by equipment
# ---------------------------------------------------------------------------
print("=" * 66)
print("AGGREGATION BY EQUIPMENT")
print("=" * 66)

aggr_eq = df_clean.group_by("equipment_id").agg([
    pl.col("temperature").count().alias("readings"),
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("temperature").min().round(2).alias("min_temp"),
    pl.col("temperature").max().round(2).alias("max_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
    pl.col("pressure").min().round(2).alias("min_pressure"),
    pl.col("pressure").max().round(2).alias("max_pressure"),
    pl.col("vibration").mean().round(2).alias("avg_vibration"),
    pl.col("rpm").mean().round(0).cast(pl.Int64).alias("avg_rpm"),
    pl.col("power_consumption").sum().round(2).alias("total_power_kw"),
]).sort("equipment_id")

print(aggr_eq)
print()

# ---------------------------------------------------------------------------
# 2. Aggregation by status
# ---------------------------------------------------------------------------
print("=" * 66)
print("AGGREGATION BY STATUS")
print("=" * 66)

aggr_status = df_clean.group_by("status").agg([
    pl.len().alias("count"),
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("temperature").std().round(2).alias("std_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
    pl.col("vibration").mean().round(2).alias("avg_vibration"),
    pl.col("power_consumption").mean().round(2).alias("avg_power"),
]).sort("status")

print(aggr_status)
print()

# ---------------------------------------------------------------------------
# 3. Summary statistics per metric
# ---------------------------------------------------------------------------
print("=" * 66)
print("GLOBAL METRIC SUMMARY")
print("=" * 66)

metrics = ["temperature", "pressure", "vibration", "rpm", "power_consumption"]
print("(using df_clean, fault rows excluded)")

summary = []
for m in metrics:
    summary.append({
        "metric": m,
        "avg": round(df_clean[m].mean(), 2),
        "min": round(df_clean[m].min(), 2),
        "max": round(df_clean[m].max(), 2),
        "std": round(df_clean[m].std(), 2),
        "sum": round(df_clean[m].sum(), 2),
        "count": df_clean[m].count(),
    })
summary_df = pl.DataFrame(summary, schema={"metric": pl.String, "avg": pl.Float64, "min": pl.Float64, "max": pl.Float64, "std": pl.Float64, "sum": pl.Float64, "count": pl.UInt32})
print(summary_df)
