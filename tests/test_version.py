"""Tests for version module."""

from wtf_restarted._version import (
    MAJOR, MINOR, PATCH, PHASE, PROJECT_PHASE,
    get_version, get_base_version, get_display_version, get_pip_version,
    __app_name__,
)


def test_app_name():
    assert __app_name__ == "wtf-restarted"


def test_version_components():
    assert isinstance(MAJOR, int)
    assert isinstance(MINOR, int)
    assert isinstance(PATCH, int)


def test_phase_valid():
    """PHASE is None (stable release) or a string like 'alpha', 'beta', 'rc1'."""
    assert PHASE is None or isinstance(PHASE, str)


def test_get_version_returns_string():
    v = get_version()
    assert isinstance(v, str)
    assert len(v) > 0


def test_base_version_format():
    base = get_base_version()
    assert base.startswith(f"{MAJOR}.{MINOR}.{PATCH}")


def test_display_version_includes_project_phase():
    display = get_display_version()
    if PROJECT_PHASE and PROJECT_PHASE != "stable":
        assert PROJECT_PHASE.upper() in display
    else:
        # Stable releases show version only
        assert display == get_base_version()


def test_pip_version_pep440():
    pip_v = get_pip_version()
    # PEP 440: no hyphens allowed
    assert "-" not in pip_v
    if PHASE:
        # Pre-release: should contain 'a' for alpha, 'b' for beta, etc.
        assert any(c.isalpha() for c in pip_v.split(".")[-1])
    else:
        # Stable: just digits and dots
        assert all(c.isdigit() or c == "." for c in pip_v)
