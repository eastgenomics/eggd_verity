from unittest.mock import MagicMock

import dash
from dash import dcc

# Mock dash.register_page to prevent PageError during import
dash.register_page = MagicMock()

from app.pages.home import create_overview_card, pages


class TestHomePage:
    def test_overview_contains_expected_modules(self):
        assert [page["title"] for page in pages] == [
            "Dashboard",
            "Raincloud Plot",
            "Metric Trends",
            "Correlation",
            "Explore Data",
            "Run level metrics",
        ]

        live_pages = [page for page in pages if page.get("href")]
        assert {page["href"] for page in live_pages} == {
            "/dashboard",
            "/plot",
            "/trends",
            "/correlation",
            "/explore",
        }

    def test_beta_and_coming_soon_statuses(self):
        assert [page["title"] for page in pages if page.get("status") == "Beta"] == [
            "Dashboard",
            "Raincloud Plot",
        ]
        coming_soon = next(
            page for page in pages if page["title"] == "Run level metrics"
        )
        assert coming_soon["status"] == "Coming soon"
        assert "href" not in coming_soon

    def test_coming_soon_card_is_not_a_link(self):
        card = create_overview_card(
            "Run level metrics",
            "Detailed metrics for individual sequencing runs.",
            status="Coming soon",
        )
        assert not isinstance(card, dcc.Link)
