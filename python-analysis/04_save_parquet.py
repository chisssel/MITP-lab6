import polars as pl
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.jsonl")
out_path = os.path.join(script_dir, "..", "go-collector", "equipment_data.parquet")

df = pl.read_ndjson(file_path)
df = df.with_columns(pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%.f%:z"))
df = df.unique()
df = df.filter(pl.col("status") != "fault")

df.write_parquet(out_path)

print(f"Saved: {out_path}")
print(f"Rows: {df.height}, Columns: {df.width}")
print(f"File size: {os.path.getsize(out_path) / 1024:.1f} KB")
print(f"Compression: zstd (default)")
print()
print("Columns saved:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")
