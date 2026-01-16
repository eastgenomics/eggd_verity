from unittest.mock import MagicMock, patch

import dash

# Mock dash.register_page
dash.register_page = MagicMock()

import pandas as pd
import plotly.graph_objects as go

from app.pages.trends import populate_assays, populate_tools, update_trends_plot


@patch("app.pages.trends.get_session")
@patch("app.pages.trends.get_assay_names")
def test_populate_assays(mock_get_names, mock_get_session):
    mock_session = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_get_names.return_value = ["Assay A", "Assay B"]

    options = populate_assays(None)
    assert options == ["Assay A", "Assay B"]


@patch("app.pages.trends.get_session")
@patch("app.pages.trends.get_available_tools")
def test_populate_tools(mock_get_tools, mock_get_session):
    mock_session = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_session
    mock_get_tools.return_value = ["Tool A", "Tool B"]

    options = populate_tools(["Assay A"])
    assert options == ["Tool A", "Tool B"]


@patch("app.pages.trends.get_session")
@patch("app.pages.trends.get_trends_data")
@patch("app.pages.trends.create_trends_figure")
@patch("app.pages.trends.TOOL_MODEL_MAP")
def test_update_trends_plot(mock_map, mock_create_fig, mock_get_data, mock_get_session):
    # Setup
    mock_session = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_session

    # Mock Tool Model
    mock_tool_model = MagicMock()
    mock_tool_model.metric_level = "sample"
    mock_map.__getitem__.return_value = mock_tool_model

    # Mock Data
    df = pd.DataFrame({"date": ["2023-01-01"], "run_folder": ["run1"]})
    grouping = {"color": None, "symbol": None}
    mock_get_data.return_value = (df, grouping)

    # Mock Figure
    mock_fig = go.Figure()
    mock_create_fig.return_value = mock_fig

    # Call
    fig = update_trends_plot(
        assay_names=["Assay A"],
        tool_name="Tool A",
        metric_names=["metric1"],
        plot_type="scatter",
        color_by=None,
        symbol_by=None,
        yaxis_transform="linear",
        stats_lines=[],
        marker_size=10,
        num_runs=10,
        sample_filter="all",
    )

    assert isinstance(fig, go.Figure)
    mock_get_data.assert_called_once()
    mock_create_fig.assert_called_once()


def test_update_trends_plot_missing_inputs():
    fig = update_trends_plot(
        assay_names=[],
        tool_name=None,
        metric_names=[],
        plot_type="scatter",
        color_by=None,
        symbol_by=None,
        yaxis_transform="linear",
        stats_lines=[],
        marker_size=10,
        num_runs=10,
        sample_filter="all",
    )
    # Should return warning figure
    assert isinstance(fig, go.Figure)
    assert "Please select at least one assay" in fig.layout.annotations[0].text
