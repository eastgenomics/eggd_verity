"""
Configuration constants for Verity ETL pipeline.
"""

from typing import Any
import logging.config
from pathlib import Path
from decouple import config
from data.utils.secrets import load_secrets

#secrets = load_secrets("verity/prod/app") TODO

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": LOG_DIR / "pipeline.log",
            "level": "INFO",
        },
        "debug_file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": LOG_DIR / "debug.log",
            "level": "DEBUG",
        },
        "app_file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": LOG_DIR / "app.log",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["app_file"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
    "root": {"handlers": ["console", "file", "debug_file"], "level": "DEBUG"},
}

IGNORE_SECTIONS: list[str] = [
    "picard_histogram",
    "picard_histogram_1",
    "picard_histogram_2",
    "picard_MarkIlluminaAdapters_histogram",
    "picard_MeanQualityByCycle_histogram",
    "multiqc_picard_quality_by_cycle",
    "multiqc_picard_quality_score_distribution",
    "picard_QualityScoreDistribution_histogram",
    "multiqc_general_stats",
]

PROD_PROJECT_PATTERN: str = r"^002_.*_(TWE|CEN|MYE|TSO500|PCAN|HRD|FH|SNP|TSOE)$"
DATABASE_FILE: str = "verity_db.sqlite3"
DATABASE_PATH: Path = PROJECT_ROOT / "data" / DATABASE_FILE
MAX_WORKERS: int = 16

#DX_TOKEN: str = secrets["DX_TOKEN"]
DX_TOKEN: str = config("DX_TOKEN")
