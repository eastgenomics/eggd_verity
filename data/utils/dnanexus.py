"""DNAnexus related utility functions."""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor

import dxpy
import pandas as pd

from data.config import DX_TOKEN

logger = logging.getLogger(__name__)


def login_to_dnanexus(token: str = DX_TOKEN) -> None:
    """
    Login to DNAnexus using auth token.

    Parameters
    ----------
    token : str, optional
        The DNAnexus authentication token, by default DX_TOKEN.

    Raises
    ------
    SystemExit
        If the login fails.
    """

    DX_SECURITY_CONTEXT = {
        "auth_token_type": "Bearer",
        "auth_token": token,
    }

    dxpy.set_security_context(DX_SECURITY_CONTEXT)

    try:
        dxpy.whoami()

        logger.info("DNAnexus login successful")

    except Exception as e:

        logger.error(f"Error login to DNAnexus: {e}")

        sys.exit(1)


def find_dx_projects(
    pattern: str,
    created_after: str | None = None,
    created_before: str | None = None,
) -> list:
    """
    Retrieves projects matching the given pattern.
    """
    res = list(
        dxpy.find_projects(
            level="VIEW",
            name=pattern,
            name_mode="regexp",
            created_after=created_after,
            created_before=created_before,
        )
    )
    logger.info(f"Found {len(res)} projects matching the pattern.")
    if not res:
        return []

    return [x["id"] for x in res]


def find_multiqc_report(project_id: str) -> pd.DataFrame | None:
    """Finds multiqc reports in a given project."""
    res = list(
        dxpy.find_data_objects(
            name="multiqc_data.json",
            project=project_id,
            recurse=True,
            classname="file",
            describe={"fields": {"name": True, "archivalState": True}},
        )
    )

    if not res:
        return None

    project_name = dxpy.DXProject(project_id).name
    report_data = [
        {
            "project_name": project_name,
            "project_id": x["project"],
            "file_id": x["id"],
            "file_name": x["describe"]["name"],
            "archival_state": x["describe"]["archivalState"],
        }
        for x in res
    ]

    return pd.DataFrame(report_data)


def unarchive_file(file_id: str, project_id: str) -> None:
    """Sends a request to unarchive a single DNAnexus file."""
    dx_file = dxpy.DXFile(file_id, project_id)
    dx_file.unarchive()


def get_multiqc_reports(project_ids: list[str]) -> pd.DataFrame | None:
    """
    Finds all multiqc_data.json files in a list of projects, handles
    unarchiving, and returns a DataFrame of the results.
    """
    if not project_ids:
        logger.warning("No project IDs provided to get_multiqc_reports.")
        return None
    
    logger.info(f"Searching for MultiQC reports in {len(project_ids)} projects...")

    max_workers = min(len(project_ids), 16)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(find_multiqc_report, project_ids)
        df = pd.concat([res for res in results if res is not None], ignore_index=True)

    if df.empty:
        logger.warning("No multiqc_data.json files found across all projects.")
        return None

    archived_files = df[df["archival_state"].isin(["archived", "archival"])]

    if not archived_files.empty:
        n_files = len(archived_files)
        logger.info(
            f"Found {n_files} archived files. Sending unarchive requests..."
        )
        with ThreadPoolExecutor(max_workers=min(max_workers, n_files)) as executor:
            executor.map(
                unarchive_file, archived_files["file_id"], archived_files["project_id"]
            )

        logger.info("\nUnarchive requests sent. Please re-run the script after a while.")
        sys.exit(0)
    
    return df


def _get_ref_genome(parts: list[str]) -> str:
    """
    Determines the reference genome based on project name parts.
    - MYE, SNP assays are always B38.
    - If '38' is present in the name, it's B38.
    - Otherwise, the default is B37.
    """
    assay = parts[-1]

    if assay in ["MYE", "SNP"]:
        return "GRCh38"

    if len(parts) > 2 and parts[-2] == "38":
        return "GRCh38"

    return "GRCh37"


def get_project_metadata(project_id: str, file_id: str) -> dict:
    """Retrieves and parses metadata for a given DNAnexus project."""
    project = dxpy.DXProject(project_id)
    name = project.name
    parts = name.split("_")

    if len(parts) < 5:
        raise ValueError(f"Project: '{name}' doesn't follow expected format")

    assay = parts[-1]
    if parts[-2] == "38":
        assay = f"{assay}38"

    date = pd.to_datetime(parts[1], format="%y%m%d", errors="coerce")
    if pd.isna(date):
        date = pd.to_datetime(project.created, unit="ms")

    return {
        "source": f"{project_id}:{file_id}",
        "run_folder": "_".join(parts[1:-1]),
        "date": date,
        "sequencer_id": parts[2],
        "assay": assay,
        "ref_genome": _get_ref_genome(parts),
    }