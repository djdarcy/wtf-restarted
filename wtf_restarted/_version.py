"""
Version information for wtf-restarted.

This file is the canonical source for version numbers.
The __version__ string is automatically updated by git hooks
with build metadata (branch, build number, date, commit hash).

Format: MAJOR.MINOR.PATCH[-PHASE]_BRANCH_BUILD-YYYYMMDD-COMMITHASH
Example: 0.1.0_main_4-20260311-a1b2c3d4

To manually update: ./scripts/update-version.sh
To bump version: edit MAJOR, MINOR, PATCH below

Version levels:
  PROJECT_PHASE: Global project maturity (prealpha -> alpha -> beta -> stable).
                 Changes rarely, when the overall project hits a threshold.
  PHASE:         Per-MINOR feature set maturity (alpha -> beta -> None).
                 Drops when a MINOR's feature set is complete.
"""

# Version components - edit these for version bumps
MAJOR = 0
MINOR = 2
PATCH = 2
PHASE = "alpha"  # Per-MINOR feature set: None, "alpha", "beta", "rc1", etc.
PRE_RELEASE_NUM = 1  # PEP 440 pre-release number (e.g., a1, b2)
PROJECT_PHASE = "alpha"  # Project-wide: "prealpha", "alpha", "beta", "stable"

# Auto-updated by git hooks - do not edit manually
__version__ = "0.2.2-alpha_main_9-20260313-5513e75e"
__app_name__ = "wtf-restarted"


def get_version():
    """Return the full version string including branch and build info."""
    return __version__


def get_display_version():
    """Return a human-friendly version string with project phase.

    Example: 'PREALPHA 0.1.0-alpha' or 'BETA 0.5.1' or '1.0.0'
    """
    base = get_base_version()
    if PROJECT_PHASE and PROJECT_PHASE != "stable":
        return f"{PROJECT_PHASE.upper()} {base}"
    return base


def get_base_version():
    """Return the semantic version string (MAJOR.MINOR.PATCH[-PHASE])."""
    if "_" in __version__:
        return __version__.split("_")[0]
    base = f"{MAJOR}.{MINOR}.{PATCH}"
    if PHASE:
        base = f"{base}-{PHASE}"
    return base


def get_pip_version():
    """
    Return PEP 440 compliant version for pip/setuptools.

    Converts our version format to PEP 440:
    - Main branch: 0.1.0-alpha_main_6-20260311-hash -> 0.1.0a1
    - Dev branch: 0.1.0-alpha_dev_6-20260311-hash -> 0.1.0a1.dev6
    """
    base = f"{MAJOR}.{MINOR}.{PATCH}"

    # Map phase to PEP 440 pre-release segment
    phase_map = {"alpha": f"a{PRE_RELEASE_NUM}", "beta": f"b{PRE_RELEASE_NUM}"}
    if PHASE:
        base += phase_map.get(PHASE, PHASE)

    if "_" not in __version__:
        return base

    parts = __version__.split("_")
    branch = parts[1] if len(parts) > 1 else "unknown"

    if branch == "main":
        return base
    else:
        build_info = "_".join(parts[2:]) if len(parts) > 2 else ""
        build_num = build_info.split("-")[0] if "-" in build_info else "0"
        return f"{base}.dev{build_num}"


# For convenience in imports
VERSION = get_version()
BASE_VERSION = get_base_version()
PIP_VERSION = get_pip_version()
DISPLAY_VERSION = get_display_version()
