import polars as pl


class TestClean:
    def test_remove_exact_duplicates(self, sample_df):
        before = sample_df.height
        df = sample_df.unique()
        assert df.height == before - 1  # one duplicate in fixture

    def test_remove_duplicates_by_key(self, sample_df):
        df = sample_df.unique(subset=["equipment_id", "timestamp"], keep="first")
        assert df.height == 6  # 7 - 1 duplicate key

    def test_remove_fault_rows(self, sample_df):
        df = sample_df.filter(pl.col("status") != "fault")
        assert df.height == 6
        assert "fault" not in df["status"].to_list()

    def test_no_fault_values_remain(self, sample_df):
        df = sample_df.filter(pl.col("status") != "fault")
        assert df["temperature"].max() < 150
        assert df["pressure"].max() < 50

    def test_temperature_is_float(self, sample_df):
        assert sample_df["temperature"].dtype == pl.Float64

    def test_rpm_is_integer(self, sample_df):
        assert sample_df["rpm"].dtype == pl.Int64

    def test_status_is_string(self, sample_df):
        assert sample_df["status"].dtype == pl.String

    def test_timestamp_is_datetime(self, sample_df):
        assert "Datetime" in str(sample_df["timestamp"].dtype)

    def test_validation_flag_marks_oob(self, sample_df):
        df = sample_df.with_columns(
            pl.when(
                (pl.col("temperature") < 0) | (pl.col("temperature") > 150)
            ).then(pl.lit("temperature_oob")).otherwise(None).alias("flag")
        )
        flagged = df.filter(pl.col("flag").is_not_null())
        assert flagged.height == 1

    def test_unique_leaves_no_duplicate_rows(self, sample_df):
        deduped = sample_df.unique()
        assert deduped.height == deduped.unique().height
