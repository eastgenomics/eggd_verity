import dxpy
import pandas as pd


def _get_ref_genome(parts: list[str]) -> str:
    """
    Determines the reference genome based on project name parts.
    - MYE, SNP assays are always B38.
    - If '38' is present in the name, it's B38.
    - Otherwise, the default is B37. ?HRD unknown 
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


def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardises DataFrame column names to snake_case following PEP8.
    """
    cols = (
        df.columns.str.strip()
        .str.lower()
        .str.replace("%", "_pct_", regex=False)
        .str.replace(r"[\s\W]+", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )

    # De-duplicate column names to prevent errors
    duplicates = cols.to_series().groupby(cols).cumcount()
    cols = cols.where(duplicates == 0, cols + "_" + duplicates.astype(str))

    df.columns = cols
    return df


def coerce_data_types(
    df: pd.DataFrame,
    max_categories: int = 10,
    cardinality: float = 0.05,
) -> pd.DataFrame:
    """
    Coerces DataFrame columns to more appropriate dtypes.
    - Uses pandas `convert_dtypes` to infer best possible dtypes.
    - Converts columns with low cardinality to 'category' type.
    """
    n_rows = len(df)
    if n_rows == 0:
        return df

    df = df.convert_dtypes()

    candidate_cols = df.select_dtypes(include=["string", "integer"]).columns

    for col in candidate_cols:
        num_unique = df[col].nunique(dropna=True)

        # skip trivial (all same / all unique)
        if num_unique == 1 or num_unique == n_rows:
            continue

        # check both absolute and relative thresholds
        if num_unique <= max_categories and (num_unique / n_rows) <= cardinality:
            df[col] = df[col].astype("category")

    return df


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = standardise_column_names(df)
    df = coerce_data_types(df)

    return df.where(pd.notna(df), None)
