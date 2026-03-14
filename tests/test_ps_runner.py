"""Tests for the shared PowerShell runner utility."""

import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from wtf_restarted.engine.ps_runner import (
    get_ps1_path,
    run_ps1,
    run_ps_command,
    _parse_json_output,
)


class TestGetPs1Path:
    """Test PowerShell script location."""

    def test_investigate_script_exists(self):
        path = get_ps1_path("investigate.ps1")
        assert path.exists()
        assert path.name == "investigate.ps1"

    def test_history_script_exists(self):
        path = get_ps1_path("history.ps1")
        assert path.exists()
        assert path.name == "history.ps1"

    def test_missing_script_raises(self):
        with pytest.raises(FileNotFoundError):
            get_ps1_path("nonexistent.ps1")


class TestRunPs1:
    """Test run_ps1 with mocked subprocess."""

    def test_returns_parsed_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"verdict": {"type": "CLEAN_RESTART"}})
        mock_result.stderr = ""

        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=mock_result):
            result = run_ps1("investigate.ps1")
            assert result["verdict"]["type"] == "CLEAN_RESTART"

    def test_passes_params_as_flags(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ok": true}'
        mock_result.stderr = ""

        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=mock_result) as mock_run:
            run_ps1("investigate.ps1", LookbackHours=72, SkipDump=True)
            cmd = mock_run.call_args[0][0]
            assert "-LookbackHours" in cmd
            assert "72" in cmd
            assert "-SkipDump" in cmd

    def test_bool_false_omits_flag(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ok": true}'
        mock_result.stderr = ""

        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=mock_result) as mock_run:
            run_ps1("investigate.ps1", SkipDump=False)
            cmd = mock_run.call_args[0][0]
            assert "-SkipDump" not in cmd

    def test_timeout_returns_error(self):
        with patch(
            "wtf_restarted.engine.ps_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="test", timeout=300),
        ):
            result = run_ps1("investigate.ps1")
            assert "error" in result
            assert "timed out" in result["error"]

    def test_powershell_not_found(self):
        with patch(
            "wtf_restarted.engine.ps_runner.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            result = run_ps1("investigate.ps1")
            assert "error" in result
            assert "PowerShell" in result["error"]

    def test_nonzero_exit_no_output(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Access denied"

        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=mock_result):
            result = run_ps1("investigate.ps1")
            assert "error" in result


class TestRunPs1Verbose:
    """Test verbose flag behavior across bool and int values."""

    def _make_mock_result(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ok": true}'
        mock_result.stderr = ""
        return mock_result

    def test_verbose_true_prints_command(self):
        """verbose=True (legacy bool) should print the 'Running:' debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=True)
                printed = " ".join(str(c) for c in mock_print.call_args_list)
                assert "Running:" in printed

    def test_verbose_1_prints_command(self):
        """verbose=1 (-v mode) should print the 'Running:' debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=1)
                printed = " ".join(str(c) for c in mock_print.call_args_list)
                assert "Running:" in printed

    def test_verbose_0_no_debug_output(self):
        """verbose=0 (default) should NOT print the 'Running:' debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=0)
                for call in mock_print.call_args_list:
                    assert "Running:" not in str(call)

    def test_verbose_negative_no_debug_output(self):
        """verbose=-1 (-Q mode) should NOT print the 'Running:' debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=-1)
                for call in mock_print.call_args_list:
                    assert "Running:" not in str(call)

    def test_verbose_negative_2_no_debug_output(self):
        """verbose=-2 (-QQ mode) should NOT print the 'Running:' debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=-2)
                for call in mock_print.call_args_list:
                    assert "Running:" not in str(call)

    def test_verbose_false_no_debug_output(self):
        """verbose=False (legacy default) should NOT print the debug line."""
        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=self._make_mock_result()):
            with patch("builtins.print") as mock_print:
                run_ps1("investigate.ps1", verbose=False)
                for call in mock_print.call_args_list:
                    assert "Running:" not in str(call)


class TestRunPsCommand:
    """Test run_ps_command for one-liners."""

    def test_returns_stdout(self):
        mock_result = MagicMock()
        mock_result.stdout = "True\n"

        with patch("wtf_restarted.engine.ps_runner.subprocess.run", return_value=mock_result):
            assert run_ps_command("echo True") == "True"

    def test_returns_none_on_failure(self):
        with patch(
            "wtf_restarted.engine.ps_runner.subprocess.run",
            side_effect=Exception("failed"),
        ):
            assert run_ps_command("bad command") is None


class TestParseJsonOutput:
    """Test JSON parsing from noisy PowerShell output."""

    def test_clean_json(self):
        result = _parse_json_output('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_after_warnings(self):
        output = 'WARNING: something\nAnother line\n{"key": "value"}'
        result = _parse_json_output(output)
        assert result == {"key": "value"}

    def test_empty_output(self):
        result = _parse_json_output("")
        assert "error" in result

    def test_no_json_at_all(self):
        result = _parse_json_output("just plain text")
        assert "error" in result

    def test_json_array_wrapped(self):
        output = '[{"a": 1}, {"a": 2}]'
        result = _parse_json_output(output)
        assert result == {"_list": [{"a": 1}, {"a": 2}]}
