from enum import IntEnum
import pandas as pd
from typing import Annotated
from pydantic import BeforeValidator


class QCStatus(IntEnum):
    """Quality control status"""

    PASS = 1
    WARNING = 2
    FAIL = 3
    NOTREPORTED = 4

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower().strip()
            if value in ("pass", "passed"):
                return cls.PASS
            if value in ("warn", "warning", "warnings"):
                return cls.WARNING
            if value in ("fail", "failed"):
                return cls.FAIL
        return cls.NOTREPORTED

    def __str__(self):
        if self == QCStatus.NOTREPORTED:
            return "Not Reported"
        return self.name.title()


class SexKaryotype(IntEnum):
    """Sex Karyotype"""

    MALE = 1
    FEMALE = 2
    UNKNOWN = 3

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower().strip()
            if value in ("male", "m"):
                return cls.MALE
            if value in ("female", "f"):
                return cls.FEMALE
        return cls.UNKNOWN

    def __str__(self):
        return self.name.title()


# A custom boolean type that handles 'NA' gracefully
NullableBool = Annotated[
    bool | None,
    BeforeValidator(lambda x: None if pd.isna(x) or x in ["NA", "N/A", ""] else x),
]