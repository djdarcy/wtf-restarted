"""
core_lib.types — Shared types for the plan-execute architecture.

Provides the foundational data structures used across the DazzleLib ecosystem:
- Action: a single operation in a plan (identity via string ID)
- ActionResult: outcome of executing an action
- Plan: ordered collection of actions with validation
- ConflictResolution: how to handle file conflicts (7 modes)
- FileCategory: classification of source/dest file comparison
- ErrorPolicy: how execute_plan() handles failures
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


# ── Enums ──────────────────────────────────────────────────────────────

class ConflictResolution(Enum):
    """How to resolve a file conflict during plan execution."""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    NEWER = "newer"
    LARGER = "larger"
    RENAME = "rename"
    FAIL = "fail"
    ASK = "ask"


class FileCategory(Enum):
    """Classification of a source/destination file comparison."""
    IDENTICAL = "identical"
    CONFLICT = "conflict"
    SOURCE_ONLY = "source_only"
    DEST_ONLY = "dest_only"


# ── Error Policy ───────────────────────────────────────────────────────

ErrorPolicy = Literal["fail_fast", "skip_deps", "continue"]
"""
How execute_plan() handles action failures:
- fail_fast:  stop immediately on first failure
- skip_deps:  skip actions depending on the failed one, continue independents
- continue:   execute everything regardless of failures
"""


# ── Core Dataclasses ───────────────────────────────────────────────────

@dataclass
class Action:
    """A single operation in a plan.

    Identity is the 'id' field (str), conventionally formatted as
    "category:operation:target" — stable across plan regeneration,
    readable in logs, enables plan composition and serialization.
    """
    id: str
    category: str
    operation: str
    target: str
    description: str
    details: dict = field(default_factory=dict)
    requires_input: bool = False
    depends_on: list[str] = field(default_factory=list)
    conflict: Optional[ConflictResolution] = None
    step: int = 0  # display ordering hint (not identity)


@dataclass
class ActionResult:
    """Outcome of executing a single action."""
    action: Action
    success: bool
    message: str = ""
    error: str = ""
    skipped: bool = False


@dataclass
class Plan:
    """An ordered collection of actions to execute.

    The plan is the single source of truth for both dry-run display
    and real execution — eliminating dry-run divergence by construction.
    """
    command: str
    actions: list[Action] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def has_changes(self) -> bool:
        """True if any action is not a skip."""
        return any(a.operation != "skip" for a in self.actions)

    def has_conflicts(self) -> bool:
        """True if any action has a non-skip conflict resolution."""
        return any(
            a.conflict is not None and a.conflict != ConflictResolution.SKIP
            for a in self.actions
        )

    def has_destructive(self) -> bool:
        """True if any action is destructive (overwrite, delete, etc)."""
        return any(
            a.operation in ("overwrite", "delete", "REINSTALL")
            for a in self.actions
        )

    def validate(self) -> list[str]:
        """Check plan integrity — returns list of error messages (empty = valid)."""
        errors = []
        ids = {a.id for a in self.actions}

        # Check for dangling dependency references
        for a in self.actions:
            for dep in a.depends_on:
                if dep not in ids:
                    errors.append(
                        f"Action '{a.id}' depends on unknown action '{dep}'"
                    )

        # Check for duplicate IDs
        seen: set[str] = set()
        for a in self.actions:
            if a.id in seen:
                errors.append(f"Duplicate action ID: '{a.id}'")
            seen.add(a.id)

        return errors

    def get_action(self, action_id: str) -> Optional[Action]:
        """Look up an action by ID."""
        for a in self.actions:
            if a.id == action_id:
                return a
        return None

    def action_ids(self) -> list[str]:
        """Return all action IDs in plan order."""
        return [a.id for a in self.actions]
