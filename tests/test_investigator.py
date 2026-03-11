"""Tests for the investigation engine (uses ps_runner under the hood)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from wtf_restarted.engine.investigator import (
    run_investigation,
    check_elevation,
)


class TestRunInvestigation:
    """Test investigation dispatch to ps_runner."""

    def test_returns_parsed_result(self):
        mock_data = {
            "system": {"computer_name": "TEST"},
            "verdict": {"type": "CLEAN_RESTART"},
        }
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value=mock_data):
            result = run_investigation()
            assert result["system"]["computer_name"] == "TEST"
            assert result["verdict"]["type"] == "CLEAN_RESTART"

    def test_passes_lookback_hours(self):
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value={}) as mock:
            run_investigation(lookback_hours=72)
            _, kwargs = mock.call_args
            assert kwargs["LookbackHours"] == 72

    def test_passes_skip_dump(self):
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value={}) as mock:
            run_investigation(skip_dump=True)
            _, kwargs = mock.call_args
            assert kwargs["SkipDump"] is True

    def test_skip_dump_false_not_passed(self):
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value={}) as mock:
            run_investigation(skip_dump=False)
            _, kwargs = mock.call_args
            assert "SkipDump" not in kwargs

    def test_passes_context_minutes(self):
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value={}) as mock:
            run_investigation(context_minutes=30)
            _, kwargs = mock.call_args
            assert kwargs["ContextMinutes"] == 30

    def test_error_propagated(self):
        with patch("wtf_restarted.engine.investigator.run_ps1", return_value={"error": "timeout"}):
            result = run_investigation()
            assert "error" in result


class TestCheckElevation:
    """Test admin elevation check via ps_runner."""

    def test_admin_returns_true(self):
        with patch("wtf_restarted.engine.investigator.run_ps_command", return_value="True"):
            assert check_elevation() is True

    def test_non_admin_returns_false(self):
        with patch("wtf_restarted.engine.investigator.run_ps_command", return_value="False"):
            assert check_elevation() is False

    def test_none_returns_false(self):
        with patch("wtf_restarted.engine.investigator.run_ps_command", return_value=None):
            assert check_elevation() is False
