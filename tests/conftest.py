"""Shared test fixtures for wtf-restarted."""

import pytest


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
