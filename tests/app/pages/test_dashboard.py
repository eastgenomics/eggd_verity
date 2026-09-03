from unittest.mock import MagicMock, patch

import dash
from dash import dcc

# Mock dash.register_page to prevent PageError during import
dash.register_page = MagicMock()

from app.pages.dashboard import (
    layout,
    update_home_page_summary,
    update_include_legacy_store,
)


class TestDashboardPageCallbacks:
    @patch("app.pages.dashboard.get_session")
    @patch("app.pages.dashboard.get_summary_stats")
    def test_update_home_page_summary_with_data(self, mock_get_stats, mock_get_session):
        """Tests the dashboard summary callback with data."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_stats.return_value = (
            [("Assay A", 10, 5, "2023-01-01", "2023-01-10")],
            [("Assay A", "Seq1", 10)],
            [("Seq1", 10)],
            [("Assay A", 1, 5)],
        )

        results = update_home_page_summary(None, False)

        assert len(results) == 6
        data = results[0]
        assert len(data) == 2
        assert data[0]["Assay"] == "Assay A"
        assert data[1]["Assay"] == "Total"
        assert "Assay A" in results[2]
        assert "Seq1" in results[3]
        assert "Assay A" in results[4]
        assert "Assay A" in results[5]

    @patch("app.pages.dashboard.get_session")
    @patch("app.pages.dashboard.get_summary_stats")
    def test_update_home_page_summary_no_data(self, mock_get_stats, mock_get_session):
        """Tests the dashboard summary callback when no data is returned."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_stats.return_value = ([], [], [], [])

        results = update_home_page_summary(None, False)

        assert results == ([], [], None, None, None, None)


class TestDashboardLegacyAssayControl:
    def test_switch_value_is_persisted_as_a_boolean(self):
        assert update_include_legacy_store(True) is True
        assert update_include_legacy_store(False) is False
        assert update_include_legacy_store(None) is False

    def test_dashboard_has_session_persistent_legacy_store(self):
        stores = [
            component
            for component in layout.children
            if isinstance(component, dcc.Store)
        ]
        legacy_store = next(
            store for store in stores if store.id == "dashboard-include-legacy-store"
        )
        assert legacy_store.storage_type == "session"
        assert legacy_store.data is False
