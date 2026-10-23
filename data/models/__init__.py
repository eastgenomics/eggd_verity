"""Data models for Verity.

Automatically imports all model submodules to ensure SQLModel tables
and SQLAlchemy relationships are registered in metadata and mappers.
"""

import importlib
import pkgutil
from pathlib import Path

# Load reports first to define BaseMetrics, Assay, Run, Sample
from . import reports
from .reports import Assay, BaseMetrics, MultiQCReport, Run, Sample

# Automatically load all other model submodules in this directory
_package_dir = Path(__file__).parent
for _, _module_name, _ in pkgutil.iter_modules([str(_package_dir)]):
    if _module_name not in ("__init__", "reports"):
        importlib.import_module(f"{__name__}.{_module_name}")

__all__ = [
    "Assay",
    "BaseMetrics",
    "MultiQCReport",
    "Run",
    "Sample",
]
