import re
from typing import Type, get_args

from data.models import reports as models
from data.models import (
    bcl2fastq,
    bclconvert,
    fastqc,
    interop,
    happy,
    picard,
    rna_seqc,
    samtools,
    sentieon,
    sex_check,
    somalier,
    sompy,
    tso500,
    vcfqc,
    verifybamid
)
from data.models.choices import QCStatus, SexKaryotype


def get_metric_models() -> dict[str, Type[models.BaseMetrics]]:
    """
    Dynamically discovers all metric models that are subclasses of BaseMetrics.

    Returns:
        A dictionary mapping a user-friendly name to the model class.
    """
    model_map = {}
    
    subclasses = set(models.BaseMetrics.__subclasses__())
    for model_cls in sorted(subclasses, key=lambda x: x.__name__):
        # Generate a user-friendly name from the class name
        # eg "SamtoolsFlagstat" -> "Samtools Flagstat"
        pretty_name = re.sub(r"(?<!^)(?=[A-Z])", " ", model_cls.__name__)
        model_map[pretty_name] = model_cls
    return model_map


def get_numeric_fields(model: Type[models.SQLModel]) -> list[str]:
    """
    Inspects a SQLModel and returns a sorted list of its numeric field names.
    Excludes common ID fields.
    """
    numeric_fields = []
    exclude_fields = {"id", "sample_id", "run_id", "assay_id"}
    for field_name, model_field in model.model_fields.items():
        if field_name in exclude_fields:
            continue

        # Handle simple types and Union types (eg int | None)
        field_types = get_args(model_field.annotation) or (model_field.annotation,)

        if any(t in (int, float) for t in field_types):
            numeric_fields.append(field_name)

    return sorted(numeric_fields)


def get_categorical_fields(model: Type[models.SQLModel]) -> list[str]:
    """
    Inspects a SQLModel and returns a sorted list of its categorical field names.
    These are fields suitable for grouping, colouring, or faceting.
    """
    categorical_fields = []
    # Exclude fields that are typically not useful for grouping due to high cardinality
    exclude_fields = {
        "id",
        "sample_id",
        "run_id",
        "assay_id",
        "source",
        "filename",
        "sample",
        "name",  # sample name
        "library",  # picard dups library
        "rg",  # verifybamid read group
    }
    for field_name, model_field in model.model_fields.items():
        if field_name in exclude_fields:
            continue

        field_types = get_args(model_field.annotation) or (model_field.annotation,)

        is_categorical = False
        for t in field_types:
            if t in (str, bool):
                is_categorical = True
                break
            # Check for Enum types
            if isinstance(t, type) and issubclass(t, (QCStatus, SexKaryotype)):
                is_categorical = True
                break

        if is_categorical:
            categorical_fields.append(field_name)

    return sorted(categorical_fields)


def get_plot_grouping_options() -> dict[str, list[str]]:
    """
    Returns a dictionary of available fields for grouping plots (color, symbol).
    Categorises them by their source model (Run, Sample, or Assay).
    """
    run_fields = get_categorical_fields(models.Run)
    sample_fields = get_categorical_fields(models.Sample)

    return {
        "Assay": ["name"],
        "Run": run_fields,
        "Sample": sample_fields,
    }
