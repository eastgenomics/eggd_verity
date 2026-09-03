from data.manager.update_assay_status import update_legacy_assays
from data.models.reports import Assay


def test_update_legacy_assays_is_dry_run_by_default(session):
    assay = Assay(name="CEN", ref_genome="B38")
    session.add(assay)
    session.commit()

    assert update_legacy_assays(session) == 1
    session.refresh(assay)
    assert assay.active is True


def test_update_legacy_assays_marks_all_matching_genomes(session):
    assays = [
        Assay(name="CEN", ref_genome="B37"),
        Assay(name="CEN", ref_genome="B38"),
        Assay(name="CURRENT", ref_genome="B38"),
    ]
    session.add_all(assays)
    session.commit()

    assert update_legacy_assays(session, dry_run=False) == 2
    assert all(not assay.active for assay in assays[:2])
    assert assays[2].active is True


def test_update_legacy_assays_is_idempotent(session):
    assay = Assay(name="TWE", active=False)
    session.add(assay)
    session.commit()

    assert update_legacy_assays(session, dry_run=False) == 0
