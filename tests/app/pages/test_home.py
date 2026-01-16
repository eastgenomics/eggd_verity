import dash
from unittest.mock import MagicMock, patch

# Mock dash.register_page to prevent PageError during import
dash.register_page = MagicMock()

from app.pages.home import update_home_page_summary


class TestHomePageCallbacks:
    @patch("app.pages.home.get_session")
    @patch("app.pages.home.get_summary_stats")
    def test_update_home_page_summary_with_data(self, mock_get_stats, mock_get_session):
        """Tests the main home page summary callback with data."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock return data from query
        mock_get_stats.return_value = (
            [("Assay A", 10, 5, "2023-01-01", "2023-01-10")],  # summary
            [("Assay A", "Seq1", 10)],  # sequencer
            [("Seq1", 10)],  # total sequencer
            [("Assay A", 1, 5)],  # sex (1=Male)
        )

        # Call callback
        results = update_home_page_summary(None)

        # Unpack and assert results (6 outputs)
        assert len(results) == 6

        # Check DataTable data
        data = results[0]
        assert len(data) == 2  # 1 row + 1 total row
        assert data[0]["Assay"] == "Assay A"
        assert data[1]["Assay"] == "Total"

        # Check JSON outputs for stores
        assert "Assay A" in results[2]  # runs_json
        assert "Seq1" in results[3]  # total_sequencer_json
        assert "Assay A" in results[4]  # sequencer_summary_json
        assert "Assay A" in results[5]  # sex_summary_json

    @patch("app.pages.home.get_session")
    @patch("app.pages.home.get_summary_stats")
    def test_update_home_page_summary_no_data(self, mock_get_stats, mock_get_session):
        """Tests the main home page summary callback when no data is returned."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_stats.return_value = ([], [], [], [])

        results = update_home_page_summary(None)
        # Should return empty lists/None for all 6 outputs
        assert results == ([], [], None, None, None, None)
