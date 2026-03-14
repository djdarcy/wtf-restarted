"""Golden file regression tests for render output.

These tests verify that render output remains identical after refactoring.
If a test fails, either the change is intentional (regenerate with
`python -m tests.generate_golden`) or it's a regression.
"""

import pytest

from tests.generate_golden import GOLDEN_SPECS, GOLDEN_DIR, capture_render


@pytest.mark.parametrize(
    "filename,func,args,kwargs",
    [(spec[0], spec[1], spec[2], spec[3]) for spec in GOLDEN_SPECS],
    ids=[spec[0].replace(".golden", "") for spec in GOLDEN_SPECS],
)
def test_golden_output(filename, func, args, kwargs):
    """Verify render output matches golden file snapshot."""
    golden_path = GOLDEN_DIR / filename
    if not golden_path.exists():
        pytest.skip(f"Golden file {filename} not found -- run: python -m tests.generate_golden")

    expected = golden_path.read_text(encoding="utf-8")
    actual = capture_render(func, *args, **kwargs)
    assert actual == expected, (
        f"Output differs from golden file {filename}. "
        f"If intentional, regenerate with: python -m tests.generate_golden"
    )
