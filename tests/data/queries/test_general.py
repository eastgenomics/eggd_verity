from datetime import datetime

from sqlmodel import Session

from data.models.reports import Assay, Run, Sample
from data.models.samtools import SamtoolsFlagstat
from data.queries.general import get_assay_names, get_available_tools


class TestGeneralQueries:
    def test_get_assay_names(self, session: Session):
        """Tests that a sorted list of unique assay names is returned."""
        session.add(Assay(name="Assay B", ref_genome="GRCh38"))
        session.add(Assay(name="Assay A", ref_genome="GRCh37"))
        session.commit()

        names = get_assay_names(session)
        assert names == ["Assay A", "Assay B"]

    def _setup_data(self, session: Session):
        assay = Assay(name="Test Assay", ref_genome="GRCh37")
        session.add(assay)
        session.commit()

        run = Run(
            run_folder="run1",
            date=datetime.now(),
            sequencer_id="seq1",
            assay_id=assay.id,
            source="project-123:file-1",
        )
        session.add(run)
        session.commit()

        sample = Sample(name="sample1", run_id=run.id)
        session.add(sample)
        session.commit()

        metric = SamtoolsFlagstat(
            sample_id=sample.id,
            total_passed=100,
            total_failed=0,
            secondary_passed=0,
            secondary_failed=0,
            supplementary_passed=0,
            supplementary_failed=0,
            duplicates_passed=0,
            duplicates_failed=0,
            mapped_passed=100,
            mapped_failed=0,
            mapped_passed_pct=100.0,
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
            flagstat_total=100,
        )
        session.add(metric)
        session.commit()

    def test_get_available_tools_with_data(self, session: Session):
        """Tests that tools with data for the selected assay are returned."""
        self._setup_data(session)
        tool_map = {"Samtools Flagstat": SamtoolsFlagstat}
        tools = get_available_tools(session, ["Test Assay"], tool_map)
        assert "Samtools Flagstat" in tools

    def test_get_available_tools_no_data(self, session: Session):
        """Tests that no tools are returned for an assay with no data."""
        self._setup_data(session)
        tool_map = {"Samtools Flagstat": SamtoolsFlagstat}
        tools = get_available_tools(session, ["Other Assay"], tool_map)
        assert tools == []

    def test_get_available_tools_no_assays_provided(self, session: Session):
        """Tests that an empty list is returned if no assays are provided."""
        tools = get_available_tools(session, [], {"Tool": SamtoolsFlagstat})
        assert tools == []
