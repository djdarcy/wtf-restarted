"""Subprocess smoke tests -- invoke the real CLI binary.

These tests run `wtf-restarted` as a subprocess, catching issues that
in-process main() calls miss: entry point config, import errors,
argparse edge cases in real argv processing.

Only tests that don't require admin/event log access belong here.
For tests that exercise diagnosis logic, use the cli_runner fixture
in test_cli.py instead.
"""

import subprocess
import sys

import pytest


def run_cli(*args, timeout=10):
    """Invoke wtf-restarted as a subprocess and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "wtf_restarted.cli", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_parse_only(*args, timeout=5):
    """Invoke Python to parse args only (no investigation).

    Uses build_parser() directly to test that argparse accepts the
    arguments without running the actual CLI pipeline.
    """
    code = (
        "from wtf_restarted.cli import build_parser; "
        "args = build_parser().parse_args(" + repr(list(args)) + "); "
        "print('OK:', vars(args))"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestSubprocessSmoke:
    """Smoke tests that invoke the real CLI binary."""

    def test_help_exits_zero(self):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "wtf-restarted" in result.stdout

    def test_version_exits_zero(self):
        result = run_cli("--version")
        assert result.returncode == 0
        assert "wtf-restarted" in result.stdout

    def test_invalid_command_exits_nonzero(self):
        result = run_cli("nonexistent")
        assert result.returncode != 0
        assert "invalid choice" in result.stderr

    def test_help_shows_ai_options(self):
        """Help text should document all AI options."""
        result = run_cli("--help")
        assert "--ai" in result.stdout
        assert "--ai-only" in result.stdout
        assert "--ai-verbose" in result.stdout


class TestSubprocessArgParsing:
    """Test that argparse accepts various flag combinations.

    These use build_parser() in a subprocess to avoid running
    the actual investigation pipeline (which needs admin + event logs).
    This is the layer that catches argparse bugs like the original
    '--ai-only prompt-only' failure.
    """

    def test_ai_only_prompt_only_parses(self):
        """The exact invocation that was broken before the nargs fix."""
        result = run_parse_only("--ai-only", "prompt-only")
        assert result.returncode == 0
        assert "invalid choice" not in result.stderr
        assert "'ai_only': 'prompt-only'" in result.stdout

    def test_ai_prompt_only_parses(self):
        result = run_parse_only("--ai", "prompt-only")
        assert result.returncode == 0
        assert "'ai': 'prompt-only'" in result.stdout

    def test_ai_only_bare_defaults_to_claude(self):
        result = run_parse_only("--ai-only")
        assert result.returncode == 0
        assert "'ai_only': 'claude'" in result.stdout

    def test_ai_bare_defaults_to_claude(self):
        result = run_parse_only("--ai")
        assert result.returncode == 0
        assert "'ai': 'claude'" in result.stdout

    def test_combined_json_ai_only(self):
        result = run_parse_only("--json", "--ai-only", "prompt-only")
        assert result.returncode == 0
        assert "'json_output': True" in result.stdout
        assert "'ai_only': 'prompt-only'" in result.stdout

    def test_ai_verbose_with_ai(self):
        result = run_parse_only("--ai", "prompt-only", "--ai-verbose")
        assert result.returncode == 0
        assert "'ai_verbose': True" in result.stdout

    def test_ai_only_and_ai_both_set(self):
        """--ai prompt-only --ai-only should set both."""
        result = run_parse_only("--ai", "prompt-only", "--ai-only")
        assert result.returncode == 0
        assert "'ai': 'prompt-only'" in result.stdout
        assert "'ai_only': 'claude'" in result.stdout

    def test_no_ai_flags_defaults(self):
        result = run_parse_only()
        assert result.returncode == 0
        assert "'ai': None" in result.stdout
        assert "'ai_only': None" in result.stdout

    def test_invalid_command_rejected(self):
        result = run_parse_only("bogus")
        assert result.returncode != 0
        assert "invalid choice" in result.stderr
