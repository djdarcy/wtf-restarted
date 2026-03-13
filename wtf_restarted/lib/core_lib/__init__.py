"""
core_lib — Shared types and protocols for the plan-execute architecture.

A types-only library with zero internal dependencies. Provides the foundational
data structures that plan_lib, file_ops, and consumer applications all share.

Public API:
    Action              — single operation in a plan (identity via string ID)
    ActionResult        — outcome of executing an action
    Plan                — ordered collection of actions with validation
    ConflictResolution  — how to handle file conflicts (7 modes)
    FileCategory        — classification of source/dest file comparison
    ErrorPolicy         — type alias for error handling strategy
    PlanRenderer        — protocol for plan display implementations
"""

from .types import (
    Action,
    ActionResult,
    Plan,
    ConflictResolution,
    FileCategory,
    ErrorPolicy,
)
from .protocols import PlanRenderer

__all__ = [
    'Action',
    'ActionResult',
    'Plan',
    'ConflictResolution',
    'FileCategory',
    'ErrorPolicy',
    'PlanRenderer',
]
