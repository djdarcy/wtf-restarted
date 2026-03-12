"""Tests for AI analyzer module."""

import json
from unittest.mock import patch

from wtf_restarted.ai.analyzer import (
    build_prompt,
    parse_response,
    analyze,
    check_available,
    get_backend,
)


# Minimal investigation result for testing
SAMPLE_RESULTS = {
    "system": {
        "boot_time": "2026-03-11 04:42:10",
        "uptime_display": "0.11:38:43",
        "computer_name": "TESTPC",
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
        "details": ["KB5079473 installed"],
    },
    "events": {},
    "dumps": {},
    "dump_analysis": {"performed": False},
}


class TestBuildPrompt:
    def test_builds_prompt_string(self):
        prompt = build_prompt(SAMPLE_RESULTS)
        assert isinstance(prompt, str)
        assert "Windows crash diagnosis expert" in prompt
        assert "INITIATED_RESTART" in prompt

    def test_includes_evidence_json(self):
        prompt = build_prompt(SAMPLE_RESULTS)
        assert "TrustedInstaller.exe" in prompt
        assert "KB5079473" in prompt

    def test_excludes_raw_output(self):
        results = {
            **SAMPLE_RESULTS,
            "dump_analysis": {
                "performed": True,
                "bugcheck_code": "0x0000007E",
                "raw_output": "HUGE RAW OUTPUT" * 1000,
            },
        }
        prompt = build_prompt(results)
        # Raw output should be in the dump section, not in evidence JSON
        assert "0x0000007E" in prompt
        assert "kd.exe" in prompt

    def test_includes_dump_section_when_available(self):
        results = {
            **SAMPLE_RESULTS,
            "dump_analysis": {
                "performed": True,
                "bugcheck_code": "0x0000009F",
                "raw_output": "FAILURE_BUCKET_ID: driver_fault",
            },
        }
        prompt = build_prompt(results)
        assert "FAILURE_BUCKET_ID" in prompt
        assert "Crash Dump Analysis" in prompt

    def test_no_dump_section_when_no_raw_output(self):
        prompt = build_prompt(SAMPLE_RESULTS)
        assert "Crash Dump Analysis" not in prompt


class TestParseResponse:
    def test_parses_structured_response(self):
        text = (
            "What Happened:\n"
            "Windows Update restarted your PC.\n\n"
            "Why:\n"
            "KB5079473 required a reboot.\n\n"
            "What To Do:\n"
            "1. No action needed.\n\n"
            "Confidence:\n"
            "High -- clear evidence of initiated restart."
        )
        sections = parse_response(text)
        assert "what_happened" in sections
        assert "Windows Update" in sections["what_happened"]
        assert "why" in sections
        assert "what_to_do" in sections
        assert "confidence" in sections
        assert "High" in sections["confidence"]

    def test_handles_unstructured_response(self):
        text = "Your PC restarted because of a Windows Update."
        sections = parse_response(text)
        assert "raw" in sections

    def test_handles_partial_sections(self):
        text = (
            "What Happened:\n"
            "BSOD caused by faulty driver.\n\n"
            "Confidence:\n"
            "Medium"
        )
        sections = parse_response(text)
        assert "what_happened" in sections
        assert "confidence" in sections


class TestBackends:
    def test_get_claude_backend(self):
        backend = get_backend("claude")
        assert hasattr(backend, "invoke")
        assert hasattr(backend, "is_available")

    def test_get_prompt_only_backend(self):
        backend = get_backend("prompt-only")
        assert backend.is_available()

    def test_unknown_backend_raises(self):
        try:
            get_backend("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestAnalyze:
    @patch("wtf_restarted.ai.backends.claude.is_available", return_value=False)
    def test_unavailable_backend(self, mock_avail):
        result = analyze(SAMPLE_RESULTS, backend_name="claude")
        assert not result["success"]
        assert "not available" in result["error"]

    def test_prompt_only_backend(self):
        result = analyze(SAMPLE_RESULTS, backend_name="prompt-only")
        assert not result["success"]  # prompt-only saves prompt, doesn't invoke AI
        assert "Prompt saved to:" in result["error"]
        assert ".wtf-restarted" in result["error"]
