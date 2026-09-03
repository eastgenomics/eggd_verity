import re
from typing import List

import fire
from sqlmodel import Session, SQLModel, create_engine, select

from data.config import DATABASE_PATH
from data.models import (
    bcl2fastq,
    bclconvert,
    fastqc,
    happy,
    interop,
    picard,
    rna_seqc,
    samtools,
    sentieon,
    sex_check,
    somalier,
    sompy,
    tso500,
    vcfqc,
    verifybamid,
)
from data.models.reports import Sample


SUFFIX_REGEX = re.compile(r"\.(bam|alignment|cram|hsmetrics)$", re.IGNORECASE)


def relink_child_foreign_keys(
    session: Session, old_sample_id: int, new_sample_id: int
) -> None:
    """
    Dynamically finds all tables referencing sample.id and updates their
    foreign keys from old_sample_id to new_sample_id.
    """
    mapper_registry = SQLModel.metadata

    # Iterate over all registered database tables
    for table in mapper_registry.tables.values():
        if table.name == "sample":
            continue

        # Check each foreign key column in the child table
        for column in table.columns:
            for fk in column.foreign_keys:
                if fk.column.table.name == "sample" and fk.column.name == "id":
                    # Construct an UPDATE statement: UPDATE child_table SET sample_id = new WHERE sample_id = old
                    update_stmt = (
                        table.update()
                        .where(column == old_sample_id)
                        .values({column.name: new_sample_id})
                    )
                    session.execute(update_stmt)


def clean_sample_suffixes(session: Session, dry_run: bool = True):
    """
    Cleans sample names ending in .bam or .alignment.
    Merges records and updates child FKs if a collision occurs.
    """
    # Find all samples with candidates for cleaning
    statement = select(Sample)
    all_samples: List[Sample] = session.exec(statement).all()

    dirty_samples = sorted(
        (s for s in all_samples if SUFFIX_REGEX.search(s.name)),
        key=lambda sample: sample.id,
    )

    print(f"Found {len(dirty_samples)} sample(s) with suffixes to clean.")

    updated_count = 0
    merged_count = 0

    for dirty_sample in dirty_samples:
        clean_name = SUFFIX_REGEX.sub("", dirty_sample.name)

        # Check if a clean sample already exists for the same run
        clean_existing_sample = session.exec(
            select(Sample).where(
                Sample.name == clean_name,
                Sample.run_id == dirty_sample.run_id,
                Sample.id != dirty_sample.id,
            )
        ).first()

        if clean_existing_sample:
            # CONFLICT SCENARIO: Clean sample already exists. Merge them.
            print(
                f"[MERGE] Sample ID {dirty_sample.id} ('{dirty_sample.name}') conflicts with "
                f"existing Clean Sample ID {clean_existing_sample.id} ('{clean_name}') on Run ID {dirty_sample.run_id}."
            )
            if not dry_run:
                # 1. Re-link foreign key references in child tables
                relink_child_foreign_keys(
                    session,
                    old_sample_id=dirty_sample.id,
                    new_sample_id=clean_existing_sample.id,
                )
                # 2. Delete the dirty sample record
                session.delete(dirty_sample)
            merged_count += 1

        else:
            # NO CONFLICT: Rename directly in place
            print(
                f"[RENAME] Updating Sample ID {dirty_sample.id}: '{dirty_sample.name}' -> '{clean_name}'"
            )
            if not dry_run:
                dirty_sample.name = clean_name
                session.add(dirty_sample)
            updated_count += 1

    if dry_run:
        print("\n[DRY RUN COMPLETE] No changes were committed to the database.")
        print(
            f"Summary: {updated_count} would be renamed, {merged_count} would be merged/deleted."
        )
    else:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        print("\n[SUCCESS] Database cleaned successfully.")
        print(f"Summary: {updated_count} renamed, {merged_count} merged/deleted.")


def main(dry_run: bool = True) -> None:
    engine = create_engine(f"sqlite:///{DATABASE_PATH}")

    with Session(engine) as session:
        clean_sample_suffixes(session, dry_run=dry_run)


if __name__ == "__main__":
    fire.Fire(main)
