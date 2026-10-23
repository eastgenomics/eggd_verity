import pandas as pd

from data.models.choices import QCStatus, SexKaryotype
from data.utils.formatting import format_categorical_columns, run_sample_counts


class TestFormattingUtils:
    def test_format_categorical_columns_with_valid_enums(self):
        """
        Verifies that integer Enum values are converted to their string representations.
        """
        df = pd.DataFrame(
            {"qc_status_col": [1, 3], "sex_col": [1, 2], "other_col": ["A", "B"]}
        )

        df_out = format_categorical_columns(
            df.copy(),
            color_by="run.qc_status",
            symbol_by="sample.sex",
            grouping_args={"color": "qc_status_col", "symbol": "sex_col"},
        )

        assert df_out["qc_status_col"].dtype == "object"
        assert str(QCStatus.PASS) in df_out["qc_status_col"].values
        assert str(QCStatus.FAIL) in df_out["qc_status_col"].values
        assert str(SexKaryotype.FEMALE) in df_out["sex_col"].values

    def test_format_categorical_columns_no_grouping(self):
        """Tests that the DataFrame is unchanged if no grouping is applied."""
        df = pd.DataFrame({"qc_status_col": [1, 0], "other_col": ["A", "B"]})
        df_out = format_categorical_columns(df.copy(), color_by=None, symbol_by=None)
        pd.testing.assert_frame_equal(df, df_out)

    def test_format_categorical_columns_with_non_enum(self):
        """
        Tests that non-enum columns are ignored and the DataFrame is processed correctly.
        """
        df = pd.DataFrame({"qc_status_col": [1, 0], "other_col": ["A", "B"]})
        df_out = format_categorical_columns(
            df.copy(),
            color_by="run.qc_status",
            symbol_by="sample.other_col",  # 'other_col' is not in the enum map
            grouping_args={"color": "qc_status_col", "symbol": "other_col"},
        )

        # qc_status_col should be formatted
        assert str(QCStatus.PASS) in df_out["qc_status_col"].values
        # other_col should remain unchanged
        assert df_out["other_col"].dtype == "object"
        assert "A" in df_out["other_col"].values


def test_run_label_strips_number_prefix():
    from data.utils.formatting import run_label

    assert run_label("002_261016_A01295_0866_BHV232DRX7_HRD") == (
        "261016_A01295_0866_BHV232DRX7_HRD"
    )
    # Names without the prefix are left alone
    assert run_label("261016_A01295_0866_BHV232DRX7_HRD") == (
        "261016_A01295_0866_BHV232DRX7_HRD"
    )


def test_run_sample_counts_shows_values_when_samples_repeat():
    df = pd.DataFrame(
        {
            "project_name": ["p1"] * 5 + ["p2"],
            "sample_name": ["s1"] * 4 + ["s2", "s3"],
            "value": [1.0, 2.0, 3.0, 4.0, None, 5.0],
        }
    )

    counts = run_sample_counts(df, "value")

    # s2 has no value, so p1 has one sample with four FASTQ values
    assert list(counts) == ["1 (4 values)"] * 5 + ["1"]
