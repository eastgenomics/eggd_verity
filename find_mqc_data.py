"""Prep files for QC Audit
- Finds dx multiqc json files
- Unarchive them if neccessary
- Saves result in a tsv file
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
import dxpy


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


def find_report(project_id: str) -> pd.DataFrame:
    """finds multiqc reports in given project"""
    res = list(
        dxpy.find_data_objects(
            name="multiqc_data.json",
            project=project_id,
            recurse=True,
            classname="file",
            describe={"fields": {"name": True, "archivalState": True}},
        )
    )

    project_name = dxpy.DXProject(project_id).name

    if not res:
        print(f"No 'multiqc_data.json' found in {project_name}")
        return

    res = [
        {
            "project_name": project_name,
            "project_id": x["project"],
            "file_id": x["id"],
            "file_name": x["describe"]["name"],
            "archival_state": x["describe"]["archivalState"],
        }
        for x in res
    ]

    return pd.DataFrame(res)


def main():
    """finds multiqc report in 002 projects."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / "mqc_data.tsv"

    prod_pattern = r"^002_.*_(TWE|CEN|MYE|TSO500|PCAN|HRD|FH|SNP|TSOE)$"
    project_ids = get_prod_projects(prod_pattern)

    with ThreadPoolExecutor(max_workers=16) as executor:
        df = pd.concat(
            executor.map(find_report, project_ids),
        )

    print(df.archival_state.value_counts())
    df.to_csv(outfile, sep="\t", index=False)

    dfx = df[df["archival_state"].isin(["archived", "archival"])]
    if dfx.empty:
        print("No files to unarchive")
        return
    print(f"Unarchiving {len(dfx)} files...")

    for _, row in dfx.iterrows():
        dx_file = dxpy.DXFile(row["file_id"], row["project_id"])
        dx_file.unarchive()

    print("All Unarchive requests sent")


if __name__ == "__main__":
    main()
