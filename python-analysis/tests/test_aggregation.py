import polars as pl


class TestAggregation:
    def test_group_by_equipment_returns_all(self, sample_df):
        df_clean = sample_df.filter(pl.col("status") != "fault")
        result = df_clean.group_by("equipment_id").agg([
            pl.len().alias("count")
        ]).sort("equipment_id")
        assert result.height == 4  # CNC-001, CNC-002, Press-001, Robot-001

    def test_group_by_equipment_counts(self, sample_df):
        df_clean = sample_df.filter(pl.col("status") != "fault")
        result = df_clean.group_by("equipment_id").agg([
            pl.len().alias("count")
        ]).sort("equipment_id")
        counts = dict(zip(result["equipment_id"], result["count"]))
        assert counts["CNC-001"] == 3  # original + duplicate + warning (all non-fault)

    def test_avg_temperature_per_equipment(self, sample_df):
        df_clean = sample_df.filter(pl.col("status") != "fault")
        result = df_clean.group_by("equipment_id").agg([
            pl.col("temperature").mean().alias("avg_temp")
        ]).sort("equipment_id")
        for row in result.iter_rows():
            if row[0] == "CNC-001":
                assert 65.0 <= row[1] <= 67.0

    def test_sum_power_consumption(self, sample_df):
        df_clean = sample_df.filter(pl.col("status") != "fault")
        total = df_clean["power_consumption"].sum()
        assert total > 0

    def test_status_grouping(self, sample_df):
        df_clean = sample_df.filter(pl.col("status") != "fault")
        result = df_clean.group_by("status").agg([
            pl.len().alias("count")
        ])
        statuses = dict(zip(result["status"], result["count"]))
        assert "normal" in statuses
        assert "warning" in statuses
