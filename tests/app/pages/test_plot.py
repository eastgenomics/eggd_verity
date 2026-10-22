from unittest.mock import MagicMock, patch

import dash

# Mock dash.register_page
dash.register_page = MagicMock()

import pandas as pd
import plotly.graph_objects as go

from app.pages.plot import layout, update_raincloud_plot, update_url


def _find(component, component_id):
    """Depth first search of a Dash layout for a component id."""
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        found = _find(child, component_id)
        if found is not None:
            return found
    return None


def test_layout_defaults_to_sequencer_colour():
    page = layout()
    assert _find(page, "plot-color-by-dropdown").value == "run.sequencer_id"
    assert _find(page, "plot-components-checklist").value == ["violin", "box", "points"]


def test_layout_reads_query_string_values():
    page = layout(num_runs="5", color_by="", plot_components="box")
    assert _find(page, "plot-num-runs-input").value == 5
    # Clearing the colour in the URL means colour by run
    assert _find(page, "plot-color-by-dropdown").value is None
    assert _find(page, "plot-components-checklist").value == ["box"]


def test_layout_does_not_leak_between_requests():
    layout(tool="Tool A")
    assert _find(layout(), "plot-tool-dropdown").value is None


def test_unchecked_components_survive_url_round_trip():
    search = update_url(["A"], "T", "m", 10, None, None, "positive", [])
    assert "plot_components=" in search
    page = layout(plot_components="")
    assert _find(page, "plot-components-checklist").value == []


@patch("app.pages.plot.get_session")
@patch("app.pages.plot.get_raincloud_data")
@patch("app.pages.plot.TOOL_MODEL_MAP")
def test_regex_with_no_matches_warns(mock_map, mock_get_data, mock_get_session):
    mock_map.__getitem__.return_value = MagicMock(metric_level="sample")
    df = pd.DataFrame(
        {
            "date": ["2023-01-01"],
            "run_folder": ["run1"],
            "m": [1.0],
            "sample_name": [None],
        }
    )
    mock_get_data.return_value = (df, {"color": None})

    fig = update_raincloud_plot(
        ["A"], "Tool A", "m", 10, "^nomatch$", None, "positive", ["violin"]
    )

    assert isinstance(fig, go.Figure)
    assert "No samples match" in fig.layout.annotations[0].text
