"""Tests for AI analyzer module."""

import json
from unittest.mock import patch

from wtf_restarted.ai.analyzer import (
    build_prompt,
    parse_response,
    analyze,
    check_available,
    get_backend,
    _cache_stable_fields,
    _cache_key,
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

    def test_get_codex_backend(self):
        backend = get_backend("codex")
        assert hasattr(backend, "invoke")
        assert hasattr(backend, "is_available")
        assert hasattr(backend, "find_cli")

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


# -- Results with events for fingerprint testing --
RESULTS_WITH_EVENTS = {
    **SAMPLE_RESULTS,
    "events": {
        "shutdown_initiator": [
            {"time": "2026-03-11 04:41:00", "message": "Restart requested"},
        ],
        "kernel_power_41": [],
        "event_6008": [],
        "bugcheck": [],
        "whea": [],
        "gpu_events": [],
        "context_window": [
            {"time": "2026-03-11 04:40:55", "message": "Some context event"},
        ],
        "windows_update": [
            {"time": "2026-03-11 04:30:00", "message": "KB5079473"},
        ],
    },
}


class TestCacheStableFields:
    def test_includes_verdict_type(self):
        fp = _cache_stable_fields(SAMPLE_RESULTS)
        assert fp["verdict_type"] == "INITIATED_RESTART"

    def test_counts_events_per_category(self):
        fp = _cache_stable_fields(RESULTS_WITH_EVENTS)
        assert fp["shutdown_initiator_count"] == 1
        assert fp["kernel_power_41_count"] == 0
        assert fp["bugcheck_count"] == 0

    def test_sorts_event_timestamps(self):
        results = {
            **SAMPLE_RESULTS,
            "events": {
                "bugcheck": [
                    {"time": "2026-03-11 05:00:00"},
                    {"time": "2026-03-11 03:00:00"},
                ],
            },
        }
        fp = _cache_stable_fields(results)
        assert fp["bugcheck_times"] == [
            "2026-03-11 03:00:00",
            "2026-03-11 05:00:00",
        ]

    def test_excludes_context_window(self):
        fp = _cache_stable_fields(RESULTS_WITH_EVENTS)
        assert "context_window_count" not in fp
        assert "context_window_times" not in fp

    def test_excludes_windows_update(self):
        fp = _cache_stable_fields(RESULTS_WITH_EVENTS)
        assert "windows_update_count" not in fp

    def test_includes_dump_analysis_when_performed(self):
        results = {
            **SAMPLE_RESULTS,
            "dump_analysis": {
                "performed": True,
                "bugcheck_code": "0x0000007E",
                "module": "nt",
                "bucket": "AV_nt!func",
            },
        }
        fp = _cache_stable_fields(results)
        assert fp["dump_bugcheck"] == "0x0000007E"
        assert fp["dump_module"] == "nt"
        assert fp["dump_bucket"] == "AV_nt!func"

    def test_marks_dump_not_performed(self):
        fp = _cache_stable_fields(SAMPLE_RESULTS)
        assert fp["dump_performed"] is False
        assert "dump_bugcheck" not in fp

    def test_evidence_flags_as_booleans(self):
        fp = _cache_stable_fields(SAMPLE_RESULTS)
        ev = fp["evidence"]
        assert ev["dirty_shutdown"] is False
        assert ev["bugcheck"] is False
        assert ev["crash_dump_exists"] is False

    def test_evidence_coerces_truthy_strings(self):
        results = {
            **SAMPLE_RESULTS,
            "evidence": {
                "dirty_shutdown": "YES",
                "bugcheck": "Event 1001",
                "whea_error": "",
                "crash_dump_exists": True,
            },
        }
        fp = _cache_stable_fields(results)
        ev = fp["evidence"]
        assert ev["dirty_shutdown"] is True
        assert ev["bugcheck"] is True
        assert ev["whea_error"] is False
        assert ev["crash_dump_exists"] is True


class TestCacheKey:
    def test_same_events_same_key(self):
        """Different --hours finding same events should produce same cache key."""
        key1 = _cache_key(RESULTS_WITH_EVENTS, "claude")
        key2 = _cache_key(RESULTS_WITH_EVENTS, "claude")
        assert key1 == key2

    def test_different_backend_different_key(self):
        key_claude = _cache_key(SAMPLE_RESULTS, "claude")
        key_prompt = _cache_key(SAMPLE_RESULTS, "prompt-only")
        assert key_claude != key_prompt

    def test_different_events_different_key(self):
        results_extra = {
            **RESULTS_WITH_EVENTS,
            "events": {
                **RESULTS_WITH_EVENTS["events"],
                "bugcheck": [{"time": "2026-03-11 04:41:05"}],
            },
        }
        key1 = _cache_key(RESULTS_WITH_EVENTS, "claude")
        key2 = _cache_key(results_extra, "claude")
        assert key1 != key2

    def test_context_window_changes_ignored(self):
        """Changing context_window events should NOT change the cache key."""
        results_more_context = {
            **RESULTS_WITH_EVENTS,
            "events": {
                **RESULTS_WITH_EVENTS["events"],
                "context_window": [
                    {"time": "2026-03-11 04:40:55", "message": "event1"},
                    {"time": "2026-03-11 04:40:50", "message": "event2"},
                    {"time": "2026-03-11 04:40:45", "message": "event3"},
                ],
            },
        }
        key1 = _cache_key(RESULTS_WITH_EVENTS, "claude")
        key2 = _cache_key(results_more_context, "claude")
        assert key1 == key2

    def test_key_is_hex_string(self):
        key = _cache_key(SAMPLE_RESULTS, "claude")
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)
