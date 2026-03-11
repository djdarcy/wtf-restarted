"""Tests for the history module."""

from unittest.mock import patch

from wtf_restarted.engine.history import get_restart_history


class TestGetRestartHistory:
    """Test history retrieval via ps_runner."""

    def test_returns_list_from_list_wrapper(self):
        mock_data = {"_list": [
            {"time": "2026-03-11 04:42:10", "type": "START", "event_id": 6005, "message": "started"},
            {"time": "2026-03-11 04:40:05", "type": "INITIATED_RESTART", "event_id": 1074, "message": "restart"},
        ]}
        with patch("wtf_restarted.engine.history.run_ps1", return_value=mock_data):
            result = get_restart_history(days=30)
            assert len(result) == 2
            assert result[0]["type"] == "START"

    def test_single_result_returns_list(self):
        mock_data = {"time": "2026-03-11 04:42:10", "type": "START", "event_id": 6005, "message": "started"}
        with patch("wtf_restarted.engine.history.run_ps1", return_value=mock_data):
            result = get_restart_history()
            assert isinstance(result, list)
            assert len(result) == 1

    def test_error_returns_empty(self):
        with patch("wtf_restarted.engine.history.run_ps1", return_value={"error": "failed"}):
            result = get_restart_history()
            assert result == []

    def test_passes_days_param(self):
        with patch("wtf_restarted.engine.history.run_ps1", return_value={"error": "mock"}) as mock:
            get_restart_history(days=90)
            _, kwargs = mock.call_args
            assert kwargs["Days"] == 90
