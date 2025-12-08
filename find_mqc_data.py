"""Prep files for QC Audit
- Finds dx multiqc json files
- Unarchive them if neccessary
- Saves result in a tsv file
"""

from pathlib import Path

import dxpy
import pandas as pd

from data.utils import get_multiqc_reports

OUTPUT_DIR = Path("data/VERITY_DATASET/source")


def get_prod_projects(pattern: str) -> list:
    """
    Retrieves projects matching the given pattern.
    """
    res = list(
        dxpy.find_projects(
            level="VIEW", name=pattern, name_mode="regexp", describe=True
        )
    )
    print(f"Found {len(res)} projects")
    if not res:
        return []

    res = [
        {
            "project_id": x["id"],
            "project_name": x["describe"]["name"],
            "assay": x["describe"]["name"].split("_")[-1],
        }
        for x in res
    ]

    res = pd.DataFrame(res)
    outfile = OUTPUT_DIR / "002_Projects.tsv"
    res.to_csv(outfile, sep="\t", index=False)
    print(res.assay.value_counts())

    return res.project_id.values


def main():
    """finds multiqc report in 002 projects."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / "mqc_data.tsv"

    prod_pattern = r"^002_.*_(TWE|CEN|MYE|TSO500|PCAN|HRD|FH|SNP|TSOE)$"
    project_ids = get_prod_projects(prod_pattern)

    df = get_multiqc_reports(project_ids)

    if df is not None:
        print("\nArchival state of found files:")
        print(df.archival_state.value_counts())
        df.to_csv(outfile, sep="\t", index=False)
        print(f"Successfully wrote details for {len(df)} live files to {outfile}")


if __name__ == "__main__":
    main()
