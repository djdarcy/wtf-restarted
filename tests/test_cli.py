"""Tests for the CLI argument parser and dispatch logic."""

import pytest
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
        assert args.verbose is True

    def test_verbose_short(self):
        args = build_parser().parse_args(["-v"])
        assert args.verbose is True

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

        def mock_diagnose(args):
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
