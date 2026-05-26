import polars as pl
import duckdb
import sys, io, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
parquet_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.parquet").replace("\\", "/")

# ===================================================================
# 1. DuckDB analysis
# ===================================================================
print("=" * 66)
print("DUCKDB SQL ANALYSIS")
print("=" * 66)

conn = duckdb.connect()

start = time.perf_counter()

result1 = conn.execute(f"""
    SELECT
        equipment_id,
        COUNT(*)                                     AS readings,
        ROUND(AVG(temperature), 2)                   AS avg_temp,
        ROUND(MIN(temperature), 2)                   AS min_temp,
        ROUND(MAX(temperature), 2)                   AS max_temp,
        ROUND(AVG(pressure), 2)                      AS avg_pressure,
        ROUND(AVG(vibration), 2)                     AS avg_vibration,
        ROUND(AVG(rpm), 0)::INT                      AS avg_rpm,
        ROUND(SUM(power_consumption), 2)             AS total_power
    FROM '{parquet_path}'
    WHERE status != 'fault'
    GROUP BY equipment_id
    ORDER BY equipment_id
""").fetchdf()

elapsed1 = time.perf_counter() - start

print("-- Aggregation by equipment --")
print(result1.to_string(index=False))
print(f"Time: {elapsed1*1000:.1f} ms")
print()

start = time.perf_counter()

result2 = conn.execute(f"""
    SELECT
        status,
        COUNT(*)                                     AS count,
        ROUND(AVG(temperature), 2)                   AS avg_temp,
        ROUND(STDDEV(temperature), 2)                AS std_temp,
        ROUND(AVG(pressure), 2)                      AS avg_pressure,
        ROUND(AVG(vibration), 2)                     AS avg_vibration,
        ROUND(AVG(power_consumption), 2)             AS avg_power
    FROM '{parquet_path}'
    WHERE status != 'fault'
    GROUP BY status
    ORDER BY status
""").fetchdf()

elapsed2 = time.perf_counter() - start

print("-- Aggregation by status --")
print(result2.to_string(index=False))
print(f"Time: {elapsed2*1000:.1f} ms")
print()

start = time.perf_counter()

result3 = conn.execute(f"""
    SELECT
        equipment_id,
        DATE_TRUNC('hour', timestamp)                AS hour,
        COUNT(*)                                     AS readings,
        ROUND(AVG(temperature), 2)                   AS avg_temp,
        ROUND(AVG(pressure), 2)                      AS avg_pressure
    FROM '{parquet_path}'
    WHERE status NOT IN ('fault', 'critical')
    GROUP BY equipment_id, DATE_TRUNC('hour', timestamp)
    ORDER BY hour, equipment_id
""").fetchdf()

elapsed3 = time.perf_counter() - start

print("-- Hourly aggregation (windowed) --")
print(result3.to_string(index=False))
print(f"Time: {elapsed3*1000:.1f} ms")

conn.close()

# ===================================================================
# 2. Polars equivalent (same queries)
# ===================================================================
print()
print("=" * 66)
print("POLARS EQUIVALENT ANALYSIS")
print("=" * 66)

df = pl.read_parquet(parquet_path)
df_clean = df.filter(pl.col("status") != "fault")

start = time.perf_counter()
p1 = df_clean.group_by("equipment_id").agg([
    pl.len().alias("readings"),
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("temperature").min().round(2).alias("min_temp"),
    pl.col("temperature").max().round(2).alias("max_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
    pl.col("vibration").mean().round(2).alias("avg_vibration"),
    pl.col("rpm").mean().round(0).cast(pl.Int64).alias("avg_rpm"),
    pl.col("power_consumption").sum().round(2).alias("total_power"),
]).sort("equipment_id")
elapsed_p1 = time.perf_counter() - start

print("-- Aggregation by equipment --")
print(p1)
print(f"Time: {elapsed_p1*1000:.1f} ms")
print()

start = time.perf_counter()
p2 = df_clean.group_by("status").agg([
    pl.len().alias("count"),
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("temperature").std().round(2).alias("std_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
    pl.col("vibration").mean().round(2).alias("avg_vibration"),
    pl.col("power_consumption").mean().round(2).alias("avg_power"),
]).sort("status")
elapsed_p2 = time.perf_counter() - start

print("-- Aggregation by status --")
print(p2)
print(f"Time: {elapsed_p2*1000:.1f} ms")
print()

start = time.perf_counter()
p3 = df.filter(
    ~pl.col("status").is_in(["fault", "critical"])
).with_columns(
    pl.col("timestamp").dt.truncate("1h").alias("hour")
).group_by("equipment_id", "hour").agg([
    pl.len().alias("readings"),
    pl.col("temperature").mean().round(2).alias("avg_temp"),
    pl.col("pressure").mean().round(2).alias("avg_pressure"),
]).sort("hour", "equipment_id")
elapsed_p3 = time.perf_counter() - start

print("-- Hourly aggregation (windowed) --")
print(p3)
print(f"Time: {elapsed_p3*1000:.1f} ms")

# ===================================================================
# 3. Performance comparison
# ===================================================================
print()
print("=" * 66)
print("PERFORMANCE COMPARISON (ms)")
print("=" * 66)
print(f"{'Query':<30} {'DuckDB':>10} {'Polars':>10} {'Winner':>10}")
print("-" * 60)
print(f"{'By equipment':<30} {elapsed1*1000:>10.2f} {elapsed_p1*1000:>10.2f} {'DuckDB' if elapsed1 < elapsed_p1 else 'Polars':>10}")
print(f"{'By status':<30} {elapsed2*1000:>10.2f} {elapsed_p2*1000:>10.2f} {'DuckDB' if elapsed2 < elapsed_p2 else 'Polars':>10}")
print(f"{'Hourly window':<30} {elapsed3*1000:>10.2f} {elapsed_p3*1000:>10.2f} {'DuckDB' if elapsed3 < elapsed_p3 else 'Polars':>10}")
