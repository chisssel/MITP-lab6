import polars as pl
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.jsonl")

df = pl.read_ndjson(file_path)
print("=" * 60)
print("STEP 0: RAW DATA")
print("=" * 60)
print(f"Rows: {df.height}, Columns: {df.width}")
print(df.head(3))
print()

# ---------------------------------------------------------------------------
# Step 1: convert types
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1: Type conversion")
print("=" * 60)

df = df.with_columns(
    pl.col("timestamp").str.to_datetime(format="%Y-%m-%dT%H:%M:%S%.f%:z"),
)
print("  timestamp: str -> datetime")

print(df.head(3))
print()

# ---------------------------------------------------------------------------
# Step 2: remove exact duplicates
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 2: Remove exact duplicate rows")
print("=" * 60)
before = df.height
df = df.unique()
after = df.height
print(f"  Before: {before}, After: {after}, Removed: {before - after}")
print()

# ---------------------------------------------------------------------------
# Step 3: handle missing values
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 3: Handle missing values")
print("=" * 60)
null_counts = df.null_count()
has_nulls = any(null_counts.row(0))

if has_nulls:
    for col in df.columns:
        n = null_counts[col][0]
        if n > 0:
            if df[col].dtype in (pl.Float64, pl.Int64):
                median_val = df[col].median()
                df = df.with_columns(pl.col(col).fill_null(median_val))
                print(f"  {col}: {n} nulls -> filled with median ({median_val})")
            else:
                df = df.with_columns(pl.col(col).fill_null("unknown"))
                print(f"  {col}: {n} nulls -> filled with 'unknown'")
else:
    print("  No missing values found")
print()

# ---------------------------------------------------------------------------
# Step 4: remove duplicates by (equipment_id, timestamp)
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 4: Remove duplicates by (equipment_id + timestamp)")
print("=" * 60)
before = df.height
df = df.unique(subset=["equipment_id", "timestamp"], keep="first")
after = df.height
print(f"  Before: {before}, After: {after}, Removed: {before - after}")
print()

# ---------------------------------------------------------------------------
# Step 5: detect and handle anomalies (fault rows)
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 5: Handle fault / anomalous readings")
print("=" * 60)

fault_rows = df.filter(pl.col("status") == "fault")
print(f"  Fault rows found: {fault_rows.height}")
if fault_rows.height > 0:
    print("  Fault rows:")
    print(fault_rows.select("equipment_id", "temperature", "pressure", "status"))

    df = df.filter(
        ~((pl.col("status") == "fault"))
    )
    print(f"  Removed {fault_rows.height} fault rows")
print()

# ---------------------------------------------------------------------------
# Step 6: validate ranges and tag out-of-bound values
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 6: Validate value ranges")
print("=" * 60)

range_checks = pl.when(
    (pl.col("temperature") < 0) | (pl.col("temperature") > 150)
).then(pl.lit("temperature_oob")).when(
    (pl.col("pressure") < 0) | (pl.col("pressure") > 50)
).then(pl.lit("pressure_oob")).when(
    (pl.col("vibration") < 0) | (pl.col("vibration") > 20)
).then(pl.lit("vibration_oob")).when(
    (pl.col("rpm") < 0)
).then(pl.lit("negative_rpm")).otherwise(None)

df = df.with_columns(range_checks.alias("validation_flag"))

flagged = df.filter(pl.col("validation_flag").is_not_null())
print(f"  Rows with validation flags: {flagged.height}")
if flagged.height > 0:
    print("  Flagged rows:")
    print(flagged.select("equipment_id", "temperature", "pressure", "rpm", "validation_flag"))
print()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("=" * 60)
print("CLEAN DATA SUMMARY")
print("=" * 60)
print(f"Final rows: {df.height}")
print(f"Columns: {df.columns}")
print(f"Types:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")
print()
print(df.head(5))
