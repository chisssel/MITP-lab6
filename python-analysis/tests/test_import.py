import polars as pl


class TestImport:
    def test_read_jsonl_returns_dataframe(self, sample_jsonl):
        df = pl.read_ndjson(sample_jsonl)
        assert isinstance(df, pl.DataFrame)

    def test_read_jsonl_columns(self, sample_jsonl):
        df = pl.read_ndjson(sample_jsonl)
        expected = {"equipment_id", "temperature", "pressure", "vibration",
                    "rpm", "power_consumption", "status", "timestamp"}
        assert set(df.columns) == expected

    def test_read_jsonl_row_count(self, sample_jsonl):
        df = pl.read_ndjson(sample_jsonl)
        assert df.height == 7

    def test_timestamp_conversion(self, sample_df):
        assert sample_df["timestamp"].dtype == pl.Datetime("us", "UTC")

    def test_no_missing_values(self, sample_df):
        nulls = sample_df.null_count()
        assert nulls.sum_horizontal()[0] == 0
