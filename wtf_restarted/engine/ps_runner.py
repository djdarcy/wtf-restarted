"""Shared PowerShell execution utilities for wtf-restarted.

All multi-line PowerShell logic lives in .ps1 files under wtf_restarted/ps1/.
This module provides two calling conventions:

    run_ps1("script.ps1", Param1=value)   -> parsed JSON dict
    run_ps_command("one-liner", timeout)   -> raw stdout string

Short one-liners (elevation check, single WMI queries) use run_ps_command().
Anything longer belongs in a .ps1 file called via run_ps1().
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_ps1_path(script_name: str) -> Path:
    """Locate a bundled PowerShell script in the ps1/ directory."""
    ps1_dir = Path(__file__).parent.parent / "ps1"
    script = ps1_dir / script_name
    if not script.exists():
        raise FileNotFoundError(f"PowerShell script not found: {script}")
    return script


def run_ps1(
    script_name: str,
    timeout: int = 300,
    verbose: bool = False,
    **params: Any,
) -> Dict:
    """Run a bundled .ps1 script and return parsed JSON output.

    Parameters are passed as -Name Value pairs to the script.
    The script is expected to output JSON (typically via ConvertTo-Json).

    Returns a dict on success, or a dict with an "error" key on failure.
    """
    script = get_ps1_path(script_name)

    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
    ]
    for name, value in params.items():
        cmd.append(f"-{name}")
        if isinstance(value, bool):
            # PowerShell switch parameters: just the flag, no value
            if not value:
                cmd.pop()  # remove the flag if False
        else:
            cmd.append(str(value))

    if verbose:
        print(f"Running: {' '.join(cmd)}", file=sys.stderr)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Script {script_name} timed out after {timeout}s"}
    except FileNotFoundError:
        return {"error": "PowerShell not found. This tool requires Windows with PowerShell."}

    if result.returncode != 0 and not result.stdout.strip():
        return {
            "error": f"PowerShell script failed (exit {result.returncode})",
            "stderr": result.stderr[:500] if result.stderr else None,
        }

    return _parse_json_output(result.stdout, script_name)


def run_ps_command(command: str, timeout: int = 10) -> Optional[str]:
    """Run a short inline PowerShell command and return raw stdout.

    Use this for one-liners only (elevation check, single queries).
    Anything longer than ~2 lines should be a .ps1 file.

    Returns stdout string on success, None on failure.
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _parse_json_output(stdout: str, source: str = "script") -> Dict:
    """Parse JSON from PowerShell output, handling noisy prefixed lines."""
    output = stdout.strip()
    if not output:
        return {"error": f"No output from {source}"}

    # Try the whole output as JSON first
    try:
        data = json.loads(output)
        if isinstance(data, list):
            return {"_list": data}
        return data
    except json.JSONDecodeError:
        pass

    # Scan backwards for a JSON object (handles warning lines before JSON)
    for line in reversed(output.split("\n")):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    return {"_list": data}
            except json.JSONDecodeError:
                continue

    return {
        "error": f"Could not parse JSON from {source}",
        "raw_output": output[:2000],
    }
