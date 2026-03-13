"""Core investigation engine -- runs PowerShell scripts and parses results."""

from .ps_runner import run_ps1, run_ps_command


def run_investigation(
    lookback_hours: int = 48,
    strict_lookback: bool = False,
    skip_dump: bool = False,
    context_minutes: int = 10,
    verbose: bool = False,
) -> dict:
    """Run the full crash investigation and return structured results.

    Returns a dict with keys: system, rdp, evidence, verdict, events, dumps,
    dump_analysis, previous_boot.
    """
    params = {
        "LookbackHours": lookback_hours,
        "ContextMinutes": context_minutes,
        "JsonOnly": True,
    }
    if strict_lookback:
        params["StrictLookback"] = True
    if skip_dump:
        params["SkipDump"] = True

    return run_ps1(
        "investigate.ps1",
        timeout=300,
        verbose=verbose,
        **params,
    )


def check_elevation() -> bool:
    """Check if we're running with admin privileges."""
    result = run_ps_command(
        "([Security.Principal.WindowsPrincipal]"
        "[Security.Principal.WindowsIdentity]::GetCurrent())"
        ".IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
    )
    return result is not None and result.lower() == "true"
