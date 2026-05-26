import polars as pl
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.jsonl")

df = pl.read_ndjson(file_path)

print("="*60)
print("FIRST 5 ROWS")
print("="*60)
print(df.head(5))
print()

print("="*60)
print("DATA INFO")
print("="*60)
print(f"Number of rows: {df.height}")
print(f"Number of columns: {df.width}")
print()

print("--- Column types ---")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")

print()
print("--- Missing values ---")
null_counts = df.null_count()
for col in df.columns:
    nulls = null_counts[col][0]
    if nulls > 0:
        print(f"  {col}: {nulls} nulls")
if null_counts.sum_horizontal()[0] == 0:
    print("  No missing values")

print()
print("--- Basic statistics for numeric columns ---")
print(df.describe())
