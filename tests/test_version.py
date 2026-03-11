"""Tests for version module."""

from wtf_restarted._version import (
    MAJOR, MINOR, PATCH, PHASE,
    get_version, get_base_version, get_display_version, get_pip_version,
    __app_name__,
)


def test_app_name():
    assert __app_name__ == "wtf-restarted"


def test_version_components():
    assert isinstance(MAJOR, int)
    assert isinstance(MINOR, int)
    assert isinstance(PATCH, int)


def test_phase_is_alpha():
    assert PHASE == "alpha"


def test_get_version_returns_string():
    v = get_version()
    assert isinstance(v, str)
    assert len(v) > 0


def test_base_version_format():
    base = get_base_version()
    assert base.startswith(f"{MAJOR}.{MINOR}.{PATCH}")


def test_display_version_includes_phase():
    display = get_display_version()
    assert "PREALPHA" in display


def test_pip_version_pep440():
    pip_v = get_pip_version()
    # PEP 440: should contain 'a' for alpha, no hyphens
    assert "-" not in pip_v
    assert "a" in pip_v
