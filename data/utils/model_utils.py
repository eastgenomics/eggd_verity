from typing import Type

# Import all metric models to ensure they are registered in BaseMetrics.__subclasses__
from data.models import bcl2fastq, bclconvert, fastqc, happy, interop, picard
from data.models import reports as models
from data.models import (
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


def get_metric_models() -> dict[str, Type[models.BaseMetrics]]:
    """
    Dynamically discovers all metric models that are subclasses of BaseMetrics.

    Returns:
        A dictionary mapping a user-friendly name to the model class.
    """
    model_map = {}
    subclasses = set(models.BaseMetrics.__subclasses__())
    for model_cls in sorted(subclasses, key=lambda x: x.__name__):
        model_map[model_cls.display_name] = model_cls
    return model_map


def get_plot_grouping_options() -> dict[str, list[str]]:
    """
    Returns a dictionary of available fields for grouping plots (color, symbol).
    Categorises them by their source model (Run, Sample, or Assay).
    """
    return {
        "Assay": models.Assay.categorical_fields,
        "Run": models.Run.categorical_fields,
        "Sample": models.Sample.categorical_fields,
    }
