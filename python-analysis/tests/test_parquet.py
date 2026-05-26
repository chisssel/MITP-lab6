import polars as pl


class TestParquet:
    def test_write_then_read_roundtrip(self, sample_df, tmp_path):
        f = tmp_path / "test.parquet"
        sample_df.write_parquet(f)
        assert f.exists()
        assert f.stat().st_size > 0

        df2 = pl.read_parquet(f)
        assert df2.height == sample_df.height
        assert df2.columns == sample_df.columns
        assert df2.schema == sample_df.schema

    def test_parquet_filters_preserved(self, sample_df, tmp_path):
        f = tmp_path / "clean.parquet"
        clean = sample_df.filter(pl.col("status") != "fault")
        clean.write_parquet(f)

        df2 = pl.read_parquet(f)
        assert "fault" not in df2["status"].to_list()
        assert df2.height == clean.height

    def test_parquet_compression(self, sample_df, tmp_path):
        f = tmp_path / "compressed.parquet"
        sample_df.write_parquet(f, compression="zstd")
        assert f.stat().st_size > 0

    def test_parquet_types_preserved(self, sample_df, tmp_path):
        f = tmp_path / "types.parquet"
        sample_df.write_parquet(f)
        df2 = pl.read_parquet(f)
        for col in sample_df.columns:
            assert df2[col].dtype == sample_df[col].dtype, (
                f"column {col}: {df2[col].dtype} != {sample_df[col].dtype}"
            )
