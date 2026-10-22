from dash import Input, Output, State, callback, html, no_update


def register_hover_callbacks(page_name, graph_id=None, extra_labels=()):
    """
    Registers the callbacks for displaying hover data for a given plot page.

    customdata[0] must be the run folder. Any further customdata values are shown
    with the matching label from ``extra_labels``.
    """
    graph_id = graph_id or f"{page_name}-plot"

    @callback(
        Output(f"{page_name}-hover-data-box", "children"),
        Input(graph_id, "hoverData"),
        State(graph_id, "figure"),
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

        lines = [f"Sample Name: {sample_name}", f"Run:         {run_folder}"]
        # Skip the x value when the x axis is the run itself
        if x_val != run_folder:
            lines.append(
                f"{x_label}: {x_val if isinstance(x_val, str) else f'{x_val:.3f}'}"
            )
        lines.append(f"{y_label}: {y_val:.3f}")

        trace = figure["data"][point["curveNumber"]]
        if group_name := trace.get("name", ""):
            if group_name != sample_name:
                lines.append(f"Group:       {group_name}")
        for label, value in zip(extra_labels, point["customdata"][1:]):
            lines.append(f"{f'{label}:':<13}{value}")

        return html.Pre("\n".join(lines), className="m-0")
