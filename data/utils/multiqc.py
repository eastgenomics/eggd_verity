"""Utility functions for handling MultiQC data from DNAnexus."""

import json

import dxpy
import pandas as pd


def read_multiqc_data(project_id: str, file_id: str) -> dict:
    """
    Reads MultiQC data from a DNAnexus MultiQC JSON file.
    """
    with dxpy.open_dxfile(file_id, project_id) as dx_file:
        multiqc_data = json.load(dx_file)["report_saved_raw_data"]
        return multiqc_data


def parse_multiqc_section(section_data: dict) -> pd.DataFrame:
    """
    Parses a MultiQC section data dictionary into a DataFrame.
    """
    df = (
        pd.DataFrame.from_dict(section_data, orient="index")
        .reset_index()
        .rename(columns={"index": "sample"})
    )
    return df