"""Generate golden file snapshots of render output for regression testing.

Usage:
    python -m tests.generate_golden          # Generate all golden files
    python -m tests.generate_golden --check  # Verify current output matches golden files

Golden files capture the exact Rich text output (ANSI stripped) for known test
data across various flag combinations. They serve as regression guards during
the Phase 3 THAC0 refactoring: after wrapping render calls in emit(), the
default output must remain identical.

Dynamic values (timestamps, uptimes) are part of the fixture data and are
fixed, so no normalization is needed.
"""

import re
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console
from rich.text import Text

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wtf_restarted.output import render

# ---------------------------------------------------------------------------
# Test data (matches conftest.py sample_diagnosis / sample_history fixtures)
# ---------------------------------------------------------------------------

SAMPLE_DIAGNOSIS = {
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

SAMPLE_HISTORY = [
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


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).resolve().parent / "test_data" / "golden"
WIDTH = 120


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def capture_render(func, *args, **kwargs):
    """Capture Rich output as plain text at fixed width.

    Writes to StringIO with no terminal emulation (force_terminal=False)
    to produce consistent plain-text output across CLI, pytest, and CI.
    """
    if func.__name__ == "render_diagnosis":
        kwargs.setdefault("interactive", False)
    buf = StringIO()
    cap_console = Console(file=buf, width=WIDTH, force_terminal=False)
    with patch("wtf_restarted.output.render.console", cap_console):
        func(*args, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Golden file definitions
# ---------------------------------------------------------------------------

# Each entry: (filename, render_function, args, kwargs)
GOLDEN_SPECS = [
    # Default diagnosis (all tiers, no paging)
    (
        "diagnosis_default.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {},
    ),
    # Verbose mode
    (
        "diagnosis_verbose.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {"verbose": True},
    ),
    # Tier 0 only
    (
        "diagnosis_tier0.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {"tiers": [0]},
    ),
    # Tier 1 only
    (
        "diagnosis_tier1.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {"tiers": [1]},
    ),
    # Tier 2 only (empty for this data -- no tier 2 content)
    (
        "diagnosis_tier2.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {"tiers": [2]},
    ),
    # Tier 0+1
    (
        "diagnosis_tier01.golden",
        render.render_diagnosis,
        [SAMPLE_DIAGNOSIS],
        {"tiers": [0, 1]},
    ),
    # History
    (
        "history_default.golden",
        render.render_history,
        [SAMPLE_HISTORY],
        {},
    ),
    # Empty history
    (
        "history_empty.golden",
        render.render_history,
        [[]],
        {},
    ),
    # Minimal/empty diagnosis
    (
        "diagnosis_empty.golden",
        render.render_diagnosis,
        [{}],
        {},
    ),
]


def generate_all():
    """Generate all golden files."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for filename, func, args, kwargs in GOLDEN_SPECS:
        output = capture_render(func, *args, **kwargs)
        path = GOLDEN_DIR / filename
        path.write_text(output, encoding="utf-8")
        print(f"  Generated: {filename} ({len(output)} chars)")
    print(f"\nWrote {len(GOLDEN_SPECS)} golden files to {GOLDEN_DIR}")


def check_all():
    """Check current output against golden files. Returns True if all match."""
    ok = True
    for filename, func, args, kwargs in GOLDEN_SPECS:
        path = GOLDEN_DIR / filename
        if not path.exists():
            print(f"  MISSING: {filename} -- run without --check to generate")
            ok = False
            continue
        expected = path.read_text(encoding="utf-8")
        actual = capture_render(func, *args, **kwargs)
        if actual == expected:
            print(f"  OK: {filename}")
        else:
            print(f"  MISMATCH: {filename}")
            # Show first difference
            exp_lines = expected.splitlines()
            act_lines = actual.splitlines()
            for i, (e, a) in enumerate(zip(exp_lines, act_lines)):
                if e != a:
                    print(f"    Line {i+1}:")
                    print(f"      expected: {e!r}")
                    print(f"      actual:   {a!r}")
                    break
            if len(exp_lines) != len(act_lines):
                print(f"    Line count: expected {len(exp_lines)}, got {len(act_lines)}")
            ok = False
    return ok


if __name__ == "__main__":
    if "--check" in sys.argv:
        print("Checking golden files...")
        if check_all():
            print("\nAll golden files match.")
        else:
            print("\nSome golden files do not match!")
            sys.exit(1)
    else:
        print("Generating golden files...")
        generate_all()
