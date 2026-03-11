"""Tests for Rich rendering output (smoke tests -- verify no exceptions)."""

from io import StringIO
from unittest.mock import patch
from rich.console import Console

from wtf_restarted.output.render import (
    render_diagnosis,
    render_history,
    VERDICT_STYLES,
)


def _capture_render(func, *args, **kwargs):
    """Capture Rich output to a string."""
    buf = StringIO()
    with patch("wtf_restarted.output.render.console", Console(file=buf, force_terminal=True)):
        func(*args, **kwargs)
    return buf.getvalue()


class TestRenderDiagnosis:
    """Smoke tests for diagnosis rendering."""

    def test_renders_without_error(self, sample_diagnosis):
        output = _capture_render(render_diagnosis, sample_diagnosis)
        assert "WTF-RESTARTED" in output
        assert "PLZWORK" in output

    def test_verdict_appears(self, sample_diagnosis):
        output = _capture_render(render_diagnosis, sample_diagnosis)
        assert "VERDICT" in output
        assert "INITIATED RESTART" in output

    def test_evidence_table(self, sample_diagnosis):
        output = _capture_render(render_diagnosis, sample_diagnosis)
        assert "Evidence Summary" in output

    def test_verbose_mode(self, sample_diagnosis):
        output = _capture_render(render_diagnosis, sample_diagnosis, verbose=True)
        assert "WTF-RESTARTED" in output

    def test_empty_data(self):
        output = _capture_render(render_diagnosis, {})
        assert "WTF-RESTARTED" in output

    def test_rdp_warning(self, sample_diagnosis):
        sample_diagnosis["rdp"] = {
            "is_rdp": True,
            "protocol": 2,
            "warning": "You are connected via RDP.",
            "disconnected_sessions": ["Session 1"],
        }
        output = _capture_render(render_diagnosis, sample_diagnosis)
        assert "RDP" in output

    def test_dump_analysis(self, sample_diagnosis):
        sample_diagnosis["dump_analysis"] = {
            "performed": True,
            "bugcheck_code": "0x0000009F",
            "module": "ntoskrnl.exe",
            "image": "ntoskrnl.exe",
            "dump_file": "C:\\Windows\\MEMORY.DMP",
        }
        output = _capture_render(render_diagnosis, sample_diagnosis)
        assert "Crash Dump" in output


class TestRenderHistory:
    """Smoke tests for history rendering."""

    def test_renders_without_error(self, sample_history):
        output = _capture_render(render_history, sample_history)
        assert "Restart History" in output

    def test_shows_events(self, sample_history):
        output = _capture_render(render_history, sample_history)
        assert "START" in output

    def test_empty_history(self):
        output = _capture_render(render_history, [])
        assert "No restart events" in output


class TestVerdictStyles:
    """Verify all verdict types have style definitions."""

    def test_all_verdicts_defined(self):
        expected = ["BSOD", "UNEXPECTED_SHUTDOWN", "INITIATED_RESTART",
                    "MIXED_SIGNALS", "CLEAN_RESTART", "UNKNOWN"]
        for v in expected:
            assert v in VERDICT_STYLES
            color, label = VERDICT_STYLES[v]
            assert isinstance(color, str)
            assert isinstance(label, str)
