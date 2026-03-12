"""Shared test fixtures for wtf-restarted."""

import pytest
from pathlib import Path
from unittest.mock import patch


# Minimal investigation result for CLI integration tests
MOCK_INVESTIGATION = {
    "system": {"boot_time": "2026-03-11", "uptime_display": "1d", "computer_name": "TEST"},
    "evidence": {"dirty_shutdown": False, "bugcheck": False, "initiated_by": None,
                 "whea_error": False, "windows_update": False, "crash_dump_exists": False},
    "verdict": {"type": "CLEAN_RESTART", "summary": "Clean restart.", "details": []},
    "events": {},
    "dumps": {},
    "dump_analysis": {"performed": False},
}


@pytest.fixture(autouse=True)
def ai_output_dir(tmp_path, monkeypatch, request):
    """Redirect prompt-only backend output to a temp directory.

    Prevents tests from leaving artifacts in ~/.wtf-restarted/ai/.
    Applied automatically to all tests.

    To keep files for analysis, mark a test with @pytest.mark.keep_ai_output:

        @pytest.mark.keep_ai_output
        def test_inspect_prompt(cli_runner, capsys):
            cli_runner(["--ai", "prompt-only"])
            # files stay in ~/.wtf-restarted/ai/ for manual inspection
    """
    if "keep_ai_output" in request.keywords:
        # Let the real _get_output_dir run
        yield Path.home() / ".wtf-restarted" / "ai"
        return

    ai_dir = tmp_path / ".wtf-restarted" / "ai"
    ai_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "wtf_restarted.ai.backends.prompt_only._get_output_dir",
        lambda: ai_dir,
    )
    yield ai_dir


@pytest.fixture
def cli_runner(monkeypatch):
    """Run main() with mocked investigation and optional AI mocking.

    Returns a callable: cli_runner(argv, ai_result=None, ai_available=True)

    The investigation layer (check_elevation, run_investigation) is always
    mocked -- those need admin privileges and event logs.

    AI mocking:
    - ai_result=dict: mocks analyze() to return that dict
    - ai_result=None: leaves analyze() unmocked (real prompt-only works,
      or pre-patch with monkeypatch for spy/custom behavior)
    - ai_available=False: mocks check_available() to return False

    Usage:
        def test_something(cli_runner, capsys):
            cli_runner(["--ai", "prompt-only"])
            out, err = capsys.readouterr()
            assert "Prompt saved" in err

        def test_with_mock_ai(cli_runner, capsys):
            ai = {"success": True, "raw_response": "x",
                  "sections": {"raw": "hi"}, "error": None}
            cli_runner(["--ai-only", "prompt-only"], ai_result=ai)
            out, err = capsys.readouterr()
            assert "VERDICT" not in out
    """
    def _run(argv, ai_result=None, ai_available=True):
        from wtf_restarted.cli import main

        # Always mock the investigation layer
        with patch("wtf_restarted.engine.investigator.check_elevation", return_value=True), \
             patch("wtf_restarted.engine.investigator.run_investigation", return_value=MOCK_INVESTIGATION):

            if ai_result is not None:
                # Mock both check_available and analyze with the provided result
                monkeypatch.setattr("wtf_restarted.ai.analyzer.check_available",
                                    lambda b: ai_available)
                monkeypatch.setattr("wtf_restarted.ai.analyzer.analyze",
                    lambda results, backend_name="claude", verbose=False, timeout=120: ai_result)
            elif not ai_available:
                # Just mock check_available to return False
                monkeypatch.setattr("wtf_restarted.ai.analyzer.check_available",
                                    lambda b: False)
            # else: no AI mocking -- real backends run (prompt-only works,
            # claude will check is_available naturally)

            main(argv)

    return _run


@pytest.fixture
def sample_diagnosis():
    """A realistic diagnosis result dict for rendering tests."""
    return {
        "system": {
            "boot_time": "2026-03-11 04:42:10",
            "uptime_display": "0.11:38:43",
            "computer_name": "PLZWORK",
        },
        "rdp": {
            "is_rdp": False,
            "protocol": 0,
        },
        "evidence": {
            "dirty_shutdown": False,
            "bugcheck": False,
            "initiated_by": "TrustedInstaller.exe",
            "whea_error": False,
            "windows_update": True,
            "crash_dump_exists": False,
        },
        "verdict": {
            "type": "INITIATED_RESTART",
            "summary": "Windows Update triggered the restart.",
            "details": [
                "KB5079473 (Security Update) installed",
                "TrustedInstaller.exe initiated reboot",
            ],
        },
        "events": {
            "kernel_power_41": [],
            "event_6008": [],
            "shutdown_initiator": [
                {
                    "time": "2026-03-11 04:40:05",
                    "message": "Process TrustedInstaller.exe initiated restart",
                }
            ],
            "windows_update": [
                {
                    "time": "2026-03-11 04:38:12",
                    "message": "KB5079473 installed successfully",
                }
            ],
            "bugcheck": [],
            "whea": [],
            "gpu_events": [],
            "context_window": [],
        },
        "dumps": {"memory_dmp": None, "minidumps": []},
        "dump_analysis": {"performed": False},
        "previous_boot": {},
    }


@pytest.fixture
def sample_history():
    """A realistic history result list."""
    return [
        {
            "time": "2026-03-11 04:42:10",
            "type": "START",
            "event_id": 6005,
            "message": "The Event log service was started.",
        },
        {
            "time": "2026-03-11 04:40:05",
            "type": "INITIATED_RESTART",
            "event_id": 1074,
            "message": "Process TrustedInstaller.exe initiated restart",
        },
        {
            "time": "2026-03-08 09:15:00",
            "type": "START",
            "event_id": 6005,
            "message": "The Event log service was started.",
        },
        {
            "time": "2026-03-08 09:13:22",
            "type": "DIRTY_SHUTDOWN",
            "event_id": 6008,
            "message": "The previous system shutdown was unexpected.",
        },
    ]
