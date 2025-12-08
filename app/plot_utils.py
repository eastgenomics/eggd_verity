import pandas as pd
from dash import Input, Output, State, callback, html, no_update

from data.models.choices import QCStatus, SexKaryotype


def format_categorical_columns(df, color_by, symbol_by, grouping_args):
    """
    Converts integer enum values in a DataFrame to their string representations.
    """
    enum_map = {
        "qc_status": QCStatus,
        "sex": SexKaryotype,
        "gender": SexKaryotype,
        "reported_sex": SexKaryotype,
        "predicted_sex": SexKaryotype,
        "original_pedigree_sex": SexKaryotype,
    }

    for arg_name, arg_val in [("color", color_by), ("symbol", symbol_by)]:
        if arg_val:
            _model_name, field_name = arg_val.split(".")
            if field_name in enum_map:
                enum_class = enum_map[field_name]
                column_alias = grouping_args[arg_name]
                if column_alias in df.columns:
                    df[column_alias] = df[column_alias].apply(
                        lambda x: str(enum_class(x)) if pd.notna(x) else "N/A"
                    )
    return df


def register_hover_callbacks(page_name):
    """
    Registers the callbacks for displaying hover data for a given plot page.
    """

    @callback(
        Output(f"{page_name}-hover-data-box", "children"),
        Input(f"{page_name}-plot", "hoverData"),
        State(f"{page_name}-plot", "figure"),
    )
    def display_hover_data(hoverData, figure):
        if hoverData is None:
            return html.P(
                "Hover over a point to see details.", className="text-muted m-2"
            )

        point = hoverData["points"][0]
        if "customdata" not in point:
            return no_update

        sample_name = point.get("hovertext", "")
        run_folder = point["customdata"][0]
        x_val, y_val = point["x"], point["y"]
        x_label, y_label = (
            figure["layout"]["xaxis"]["title"]["text"],
            figure["layout"]["yaxis"]["title"]["text"],
        )

        lines = [
            f"Sample Name: {sample_name}",
            f"Run Folder:  {run_folder}",
            f"{x_label}: {x_val if isinstance(x_val, str) else f'{x_val:.3f}'}",
            f"{y_label}: {y_val:.3f}",
        ]

        trace = figure["data"][point["curveNumber"]]
        if group_name := trace.get("name", ""):
            if group_name != sample_name:
                lines.append(f"Group:       {group_name}")
        if len(point["customdata"]) > 1:
            lines.append(f"Metric:      {point['customdata'][1]}")

        return html.Pre("\n".join(lines), className="m-0")
