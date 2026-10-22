import fire
from sqlmodel import Session, select

from data.database import get_engine
from data.models import Assay

LEGACY_ASSAY_NAMES = {"CEN", "FH", "SNP", "TSOE", "TWE"}


def update_legacy_assays(session: Session, dry_run: bool = True) -> int:
    """Mark configured legacy assays inactive, optionally committing changes."""
    statement = select(Assay).where(Assay.name.in_(LEGACY_ASSAY_NAMES))
    assays = session.exec(statement).all()
    changed_count = 0

    for assay in assays:
        status = "already inactive" if not assay.active else "marking inactive"
        print(f"[{status.upper()}] {assay.name} ({assay.ref_genome})")
        if assay.active:
            changed_count += 1
            if not dry_run:
                assay.active = False
                session.add(assay)

    print(f"Found {len(assays)} configured legacy assay(s).")
    if dry_run:
        print(f"[DRY RUN COMPLETE] {changed_count} assay(s) would be updated.")
    else:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        print(f"[SUCCESS] Updated {changed_count} assay(s).")
    return changed_count


def main(dry_run: bool = True) -> None:
    engine = get_engine()
    with Session(engine) as session:
        update_legacy_assays(session, dry_run=dry_run)


if __name__ == "__main__":
    fire.Fire(main)
