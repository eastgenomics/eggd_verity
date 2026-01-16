from dash import Input, Output, State, callback, html, no_update


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
