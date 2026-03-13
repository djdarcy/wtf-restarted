"""
Hint dataclass and global registry.

Extracted from utils.output to live in the log_lib package.
The hint registry is a global dictionary populated by domain modules
at import time via register_hint()/register_hints().
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


@dataclass
class Hint:
    """A templatized hint that can be shown in specific contexts.

    Modules create Hint instances and register them via register_hint().
    The OutputManager.hint() method handles context filtering, verbosity
    gating, and session deduplication.

    Attributes:
        id: Unique dot-namespaced identifier (e.g., 'quantifier.use_for_any')
        message: Template string with {var} placeholders for str.format()
        context: Set of contexts where this hint applies:
            'error'   - shown alongside error messages
            'result'  - shown after successful results
            'verbose' - shown only when verbosity >= min_level
        min_level: Minimum verbosity level for display
        category: Grouping key for channel filtering (e.g., 'quantifier', 'bounds')
    """
    id: str
    message: str
    context: Set[str] = field(default_factory=lambda: {'verbose'})
    min_level: int = 1
    category: str = 'general'


# Global hint registry — populated by modules at import time
_HINTS: Dict[str, Hint] = {}


def register_hint(hint: Hint) -> None:
    """Register a hint in the global registry.

    Typically called at module level so hints are available as soon as
    the module is imported. Duplicate IDs overwrite silently (allows
    reloading during development).
    """
    _HINTS[hint.id] = hint


def register_hints(*hints: Hint) -> None:
    """Register multiple hints at once."""
    for h in hints:
        register_hint(h)


def get_hint(hint_id: str) -> Optional[Hint]:
    """Look up a hint by ID. Returns None if not found."""
    return _HINTS.get(hint_id)


def get_hints_by_category(category: str) -> list:
    """Get all registered hints in a category."""
    return [h for h in _HINTS.values() if h.category == category]
