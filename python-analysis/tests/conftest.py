import polars as pl
import pytest
from datetime import datetime, timezone


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create a small JSONL file with realistic equipment data."""
    data = [
        '{"equipment_id":"CNC-001","temperature":65.2,"pressure":3.5,"vibration":0.8,"rpm":12000,"power_consumption":5.2,"status":"normal","timestamp":"2026-05-26T10:00:00.000000+00:00"}',
        '{"equipment_id":"CNC-002","temperature":62.1,"pressure":3.4,"vibration":0.6,"rpm":11800,"power_consumption":4.9,"status":"normal","timestamp":"2026-05-26T10:00:10.000000+00:00"}',
        '{"equipment_id":"Press-001","temperature":45.0,"pressure":12.0,"vibration":1.2,"rpm":800,"power_consumption":15.0,"status":"normal","timestamp":"2026-05-26T10:00:20.000000+00:00"}',
        '{"equipment_id":"Robot-001","temperature":38.0,"pressure":6.0,"vibration":0.3,"rpm":2000,"power_consumption":3.5,"status":"normal","timestamp":"2026-05-26T10:00:30.000000+00:00"}',
        '{"equipment_id":"CNC-001","temperature":66.8,"pressure":3.7,"vibration":0.9,"rpm":11950,"power_consumption":5.4,"status":"warning","timestamp":"2026-05-26T10:01:00.000000+00:00"}',
        '{"equipment_id":"Press-001","temperature":999,"pressure":999,"vibration":999,"rpm":0,"power_consumption":0,"status":"fault","timestamp":"2026-05-26T10:01:10.000000+00:00"}',
        '{"equipment_id":"CNC-001","temperature":65.2,"pressure":3.5,"vibration":0.8,"rpm":12000,"power_consumption":5.2,"status":"normal","timestamp":"2026-05-26T10:00:00.000000+00:00"}',
    ]
    f = tmp_path / "test_data.jsonl"
    f.write_text("\n".join(data), encoding="utf-8")
    return str(f)


@pytest.fixture
def sample_df(sample_jsonl):
    """Load sample JSONL into Polars DataFrame."""
    df = pl.read_ndjson(sample_jsonl)
    return df.with_columns(
        pl.col("timestamp").str.to_datetime("%Y-%m-%dT%H:%M:%S%.f%:z")
    )
