"""Hover box shared by the Trends and Raincloud pages."""

import dash
from dash._callback_context import context_value
from dash._utils import AttributeDict

from app.utils import register_hover_callbacks

FIGURE = {
    "data": [{"name": "A01303"}],
    "layout": {"xaxis": {"title": {"text": "Run"}}, "yaxis": {"title": {"text": "Q30"}}},
}
HOVER = {
    "points": [
        {
            "hovertext": "s1",
            "customdata": ["002_261004_A01303_0863_AHH3T3DMX2_MYE", "2026-10-04", 79],
            "x": "002_261004_A01303_0863_AHH3T3DMX2_MYE",
            "y": 52.7012,
            "curveNumber": 0,
        }
    ]
}


def _hover_callback():
    dash.Dash(__name__)
    register_hover_callbacks("hovertest", extra_labels=("Date", "Samples"))
    key = next(k for k in dash._callback.GLOBAL_CALLBACK_MAP if "hovertest" in k)
    return dash._callback.GLOBAL_CALLBACK_MAP[key]["callback"]


def _call(func, prop):
    context_value.set(AttributeDict(triggered_inputs=[{"prop_id": prop, "value": None}]))
    return func.__wrapped__(HOVER, FIGURE)


def test_hover_box_shows_point_details():
    box = _call(_hover_callback(), "hovertest-plot.hoverData")
    assert box.children.splitlines() == [
        "Sample:  s1",
        "Run:     002_261004_A01303_0863_AHH3T3DMX2_MYE",
        "Q30: 52.701",
        "Group:   A01303",
        "Date:    2026-10-04",
        "Samples: 79",
    ]


def test_blank_extra_value_is_left_out():
    func = _hover_callback()
    context_value.set(
        AttributeDict(triggered_inputs=[{"prop_id": "hovertest-plot.hoverData"}])
    )
    point = {**HOVER["points"][0], "customdata": [*HOVER["points"][0]["customdata"][:2], None]}
    box = func.__wrapped__({"points": [point]}, FIGURE)
    assert "Samples" not in box.children


def test_hover_box_resets_when_figure_changes():
    box = _call(_hover_callback(), "hovertest-plot.figure")
    assert box.children == "Hover over a point to see details."
