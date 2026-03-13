"""Tests for the CLI argument parser and dispatch logic."""

import json

import pytest
from unittest.mock import patch
from wtf_restarted.cli import build_parser, main


class TestBuildParser:
    """Test argument parsing."""

    def test_default_command(self):
        args = build_parser().parse_args([])
        assert args.command == "diagnose"

    def test_diagnose_command(self):
        args = build_parser().parse_args(["diagnose"])
        assert args.command == "diagnose"

    def test_history_command(self):
        args = build_parser().parse_args(["history"])
        assert args.command == "history"

    def test_default_hours(self):
        args = build_parser().parse_args([])
        assert args.hours == 48

    def test_custom_hours(self):
        args = build_parser().parse_args(["--hours", "72"])
        assert args.hours == 72

    def test_short_hours(self):
        args = build_parser().parse_args(["-H", "24"])
        assert args.hours == 24

    def test_skip_dump(self):
        args = build_parser().parse_args(["--skip-dump"])
        assert args.skip_dump is True

    def test_skip_dump_default(self):
        args = build_parser().parse_args([])
        assert args.skip_dump is False

    def test_context_minutes(self):
        args = build_parser().parse_args(["--context-minutes", "30"])
        assert args.context_minutes == 30

    def test_context_minutes_default(self):
        args = build_parser().parse_args([])
        assert args.context_minutes == 10

    def test_days_option(self):
        args = build_parser().parse_args(["history", "--days", "90"])
        assert args.days == 90

    def test_days_default(self):
        args = build_parser().parse_args([])
        assert args.days == 30

    def test_json_output(self):
        args = build_parser().parse_args(["--json"])
        assert args.json_output is True

    def test_verbose(self):
        args = build_parser().parse_args(["--verbose"])
        assert args.verbose == 1

    def test_verbose_short(self):
        args = build_parser().parse_args(["-v"])
        assert args.verbose == 1

    def test_verbose_stacking(self):
        args = build_parser().parse_args(["-vvv"])
        assert args.verbose == 3

    # -- AI argument parsing --

    def test_ai_default_off(self):
        args = build_parser().parse_args([])
        assert args.ai is None

    def test_ai_flag_defaults_to_claude(self):
        args = build_parser().parse_args(["--ai"])
        assert args.ai == "claude"

    def test_ai_explicit_backend(self):
        args = build_parser().parse_args(["--ai", "prompt-only"])
        assert args.ai == "prompt-only"

    def test_ai_only_defaults_to_claude(self):
        args = build_parser().parse_args(["--ai-only"])
        assert args.ai_only == "claude"

    def test_ai_only_explicit_backend(self):
        """wtf-restarted --ai-only prompt-only should NOT fail."""
        args = build_parser().parse_args(["--ai-only", "prompt-only"])
        assert args.ai_only == "prompt-only"

    def test_ai_only_default_off(self):
        args = build_parser().parse_args([])
        assert args.ai_only is None

    def test_ai_verbose_default_off(self):
        args = build_parser().parse_args([])
        assert args.ai_verbose is False

    def test_ai_verbose_flag(self):
        args = build_parser().parse_args(["--ai", "--ai-verbose"])
        assert args.ai_verbose is True

    def test_ai_only_with_ai_flag(self):
        """--ai prompt-only --ai-only should use prompt-only from --ai."""
        args = build_parser().parse_args(["--ai", "prompt-only", "--ai-only"])
        assert args.ai == "prompt-only"
        assert args.ai_only == "claude"  # --ai-only's own default

    def test_invalid_command(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["invalid"])

    def test_version(self):
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["--version"])
        assert exc_info.value.code == 0


class TestMainDispatch:
    """Test that main() dispatches to the correct command handler."""

    def test_diagnose_dispatch(self, monkeypatch):
        called = {}

        def mock_diagnose(args, argv=None):
            called["diagnose"] = True

        monkeypatch.setattr("wtf_restarted.cli._cmd_diagnose", mock_diagnose)
        main([])
        assert called.get("diagnose") is True

    def test_history_dispatch(self, monkeypatch):
        called = {}

        def mock_history(args):
            called["history"] = True

        monkeypatch.setattr("wtf_restarted.cli._cmd_history", mock_history)
        main(["history"])
        assert called.get("history") is True


# -- AI integration tests using cli_runner fixture --

_MOCK_AI_SUCCESS = {
    "success": True,
    "raw_response": "test response",
    "sections": {
        "what_happened": "Windows Update restarted your PC.",
        "why": "KB5079473 required a reboot.",
        "what_to_do": "1. No action needed.",
        "confidence": "High -- clear evidence.",
    },
    "error": None,
}

_MOCK_AI_FAILURE = {
    "success": False,
    "raw_response": "",
    "sections": {},
    "error": "Claude CLI timed out",
}


class TestAIOnlyImpliesAI:
    """Test that --ai-only properly sets the backend for --ai."""

    def test_ai_only_sets_backend(self, cli_runner, capsys, monkeypatch):
        """--ai-only prompt-only should invoke AI with prompt-only backend."""
        called = {}

        def spy_analyze(results, backend_name="claude", verbose=False, timeout=120, refresh=False):
            called["backend"] = backend_name
            return {"success": False, "raw_response": "", "sections": {},
                    "error": "Prompt saved to: test.md\nPaste this prompt."}

        # Pre-patch analyze with our spy before cli_runner calls main()
        monkeypatch.setattr("wtf_restarted.ai.analyzer.check_available", lambda b: True)
        monkeypatch.setattr("wtf_restarted.ai.analyzer.analyze", spy_analyze)
        cli_runner(["--ai-only", "prompt-only"])
        assert called["backend"] == "prompt-only"

    def test_ai_only_bare_defaults_to_claude(self, cli_runner, monkeypatch):
        """--ai-only with no backend should default to claude."""
        with pytest.raises(SystemExit):
            cli_runner(["--ai-only"], ai_available=False)

    def test_ai_only_suppresses_standard_output(self, cli_runner, capsys):
        """--ai-only should not render the standard diagnosis tables."""
        cli_runner(["--ai-only", "prompt-only"],
                   ai_result={**_MOCK_AI_SUCCESS, "sections": {"raw": "AI says hello"}})
        out, err = capsys.readouterr()
        assert "VERDICT" not in out
        assert "Evidence Summary" not in out


class TestAIPromptOnlyIntegration:
    """Integration test: prompt-only backend saves file and reports path."""

    def test_prompt_only_saves_and_reports(self, cli_runner, capsys):
        """--ai prompt-only should save prompt and print path (not 'failed')."""
        cli_runner(["--ai", "prompt-only"])
        out, err = capsys.readouterr()
        assert "failed" not in err.lower()
        assert "Prompt saved to:" in err
        assert ".wtf-restarted" in err


class TestJSONOutput:
    """Test JSON output modes with and without AI."""

    def test_json_without_ai(self, cli_runner, capsys):
        """--json alone should output investigation results as JSON."""
        cli_runner(["--json"])
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert "verdict" in data
        assert data["verdict"]["type"] == "CLEAN_RESTART"
        assert "ai_analysis" not in data

    def test_json_with_ai_merges_ai_key(self, cli_runner, capsys):
        """--json --ai should merge ai_analysis into the JSON output."""
        cli_runner(["--json", "--ai", "prompt-only"], ai_result=_MOCK_AI_SUCCESS)
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert "verdict" in data
        assert "ai_analysis" in data
        ai = data["ai_analysis"]
        assert ai["success"] is True
        assert ai["backend"] == "prompt-only"
        assert ai["sections"]["what_happened"] == "Windows Update restarted your PC."
        assert ai["error"] is None

    def test_json_ai_only(self, cli_runner, capsys):
        """--json --ai-only should output JSON with ai_analysis, no standard render."""
        cli_runner(["--json", "--ai-only", "prompt-only"], ai_result=_MOCK_AI_SUCCESS)
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert "ai_analysis" in data
        assert data["ai_analysis"]["success"] is True
        assert "VERDICT" not in out.split("{")[0]

    def test_json_ai_failed_includes_error(self, cli_runner, capsys):
        """--json --ai with failed backend should include error in JSON."""
        cli_runner(["--json", "--ai", "prompt-only"], ai_result=_MOCK_AI_FAILURE)
        out, err = capsys.readouterr()
        data = json.loads(out)
        assert "ai_analysis" in data
        assert data["ai_analysis"]["success"] is False
        assert "timed out" in data["ai_analysis"]["error"]

    def test_no_progress_indicator_in_json_mode(self, cli_runner, capsys):
        """--json --ai should NOT print 'Running AI analysis...' to stderr."""
        cli_runner(["--json", "--ai", "prompt-only"], ai_result=_MOCK_AI_SUCCESS)
        out, err = capsys.readouterr()
        assert "Running AI analysis" not in err
