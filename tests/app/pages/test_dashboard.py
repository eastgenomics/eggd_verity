from unittest.mock import MagicMock, patch

import dash

# Mock dash.register_page to prevent PageError during import
dash.register_page = MagicMock()

from app.pages.dashboard import update_home_page_summary


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

        results = update_home_page_summary(None)

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

        results = update_home_page_summary(None)

        assert results == ([], [], None, None, None, None)
