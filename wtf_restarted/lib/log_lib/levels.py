"""
THAC0 verbosity level constants.

These are informational — the system uses raw integers, not these constants.
They exist for readability and documentation. The emit rule is simple:

    message.level <= threshold  →  message is shown

The threshold is either the global verbosity or a per-channel override.

Level assignments:
    ←── quieter ────────── default ────────── louder ──→
    -4    -3     -2     -1     0     1      2      3
    wall  errors warnings minimal default timing config debug
"""

# Positive levels (verbose output, shown with -v/-vv/-vvv)
DEBUG = 3          # Internal state, evaluation trace
CONFIG = 2         # Configuration, algorithm selection
TIMING = 1         # Progress, timing, summary info
DEFAULT = 0        # Default output, result-context hints

# Negative levels (quiet suppression, activated with -Q/-QQ/-QQQ/-QQQQ)
MINIMAL = -1       # Suppress hints
WARNING = -2       # Suppress progress
ERROR = -3         # Errors only
NOTHING = -4       # Hard wall — exit code only (CI/headless)
