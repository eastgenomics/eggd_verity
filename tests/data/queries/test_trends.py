from datetime import date, datetime

from sqlmodel import Session

from data.models.reports import Assay, Run, Sample
from data.models.samtools import SamtoolsFlagstat
from data.queries.trends import get_trends_data


class TestTrendsQueries:
    def _setup_data(self, session: Session):
        """Helper to create common test data."""
        assay = Assay(name="Trend Assay", ref_genome="GRCh37")
        session.add(assay)
        session.commit()

        run = Run(
            run_folder="run_trend",
            date=datetime(2023, 1, 1),
            sequencer_id="seq1",
            assay_id=assay.id,
            source="project-123:file-1",
        )
        session.add(run)
        session.commit()

        sample = Sample(name="sample_trend", run_id=run.id)
        session.add(sample)
        session.commit()

        metric = SamtoolsFlagstat(
            sample_id=sample.id,
            total_passed=1000,
            total_failed=0,
            secondary_passed=0,
            secondary_failed=0,
            supplementary_passed=0,
            supplementary_failed=0,
            duplicates_passed=0,
            duplicates_failed=0,
            mapped_passed=900,
            mapped_failed=0,
            mapped_passed_pct=90.0,
            paired_in_sequencing_passed=0,
            paired_in_sequencing_failed=0,
            read1_passed=0,
            read1_failed=0,
            read2_passed=0,
            read2_failed=0,
            properly_paired_passed=0,
            properly_paired_failed=0,
            with_itself_and_mate_mapped_passed=0,
            with_itself_and_mate_mapped_failed=0,
            singletons_passed=0,
            singletons_failed=0,
            with_mate_mapped_to_a_different_chr_passed=0,
            with_mate_mapped_to_a_different_chr_failed=0,
            with_mate_mapped_to_a_different_chr_mapq_5_passed=0,
            with_mate_mapped_to_a_different_chr_mapq_5_failed=0,
            flagstat_total=1000,
        )
        session.add(metric)
        session.commit()

    def test_get_trends_data_with_data(self, session: Session):
        """Tests fetching trends data successfully."""
        self._setup_data(session)
        df, grouping = get_trends_data(
            session,
            assay_names=["Trend Assay"],
            tool_model=SamtoolsFlagstat,
            metric_names=["mapped_passed"],
            num_runs=10,
            sample_filter="all",
            color_by=None,
            symbol_by=None,
        )

        assert not df.empty
        assert len(df) == 1
        assert df.iloc[0]["mapped_passed"] == 900
        assert df.iloc[0]["run_folder"] == "run_trend"
        assert df.iloc[0]["date"] == date(2023, 1, 1)
        assert grouping == {"color": None, "symbol": None}

    def test_get_trends_data_no_data(self, session: Session):
        """Tests that an empty DataFrame with correct columns is returned."""
        df, grouping = get_trends_data(
            session,
            assay_names=["NonExistent"],
            tool_model=SamtoolsFlagstat,
            metric_names=["mapped_passed"],
            num_runs=10,
            sample_filter="all",
            color_by=None,
            symbol_by=None,
        )
        assert df.empty
        assert "date" in df.columns
        assert "run_folder" in df.columns
