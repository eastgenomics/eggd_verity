from datetime import datetime

from sqlmodel import Session

from data.models.reports import Assay, Run
from data.queries.explore import get_runs_for_assay


class TestExploreQueries:
    def test_get_runs_for_assay_with_data(self, session: Session):
        """Tests fetching runs for an existing assay."""
        assay = Assay(name="Explore Assay", ref_genome="GRCh37")
        session.add(assay)
        session.commit()

        run1 = Run(
            run_folder="run_exp_1",
            date=datetime(2023, 1, 1),
            sequencer_id="seq1",
            assay_id=assay.id,
            source="project-123:file-1",
        )
        run2 = Run(
            run_folder="run_exp_2",
            date=datetime(2023, 1, 2),
            sequencer_id="seq1",
            assay_id=assay.id,
            source="project-123:file-2",
        )
        session.add(run1)
        session.add(run2)
        session.commit()

        fetched_assay, runs = get_runs_for_assay(session, "Explore Assay")
        assert fetched_assay.id == assay.id
        assert len(runs) == 2
        assert {r.run_folder for r in runs} == {"run_exp_1", "run_exp_2"}

    def test_get_runs_for_assay_not_found(self, session: Session):
        """Tests fetching runs for a non-existent assay."""
        fetched_assay, runs = get_runs_for_assay(session, "NonExistent")
        assert fetched_assay is None
        assert runs == []
