"""Restart history -- enumerate past restart events over a time range."""

from typing import List, Dict

from .ps_runner import run_ps1


def get_restart_history(days: int = 30) -> List[Dict]:
    """Get a list of restart events over the specified number of days.

    Returns a list of dicts with keys: time, type, event_id, message.
    Types: START, CLEAN_STOP, DIRTY_SHUTDOWN, INITIATED_RESTART, BSOD.
    """
    result = run_ps1("history.ps1", timeout=30, Days=days)

    # Handle the runner's JSON parsing
    if "error" in result:
        return []

    # run_ps1 wraps list results in {"_list": [...]}
    if "_list" in result:
        data = result["_list"]
    else:
        data = result

    # PowerShell returns a single object (not array) if only one result
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []
