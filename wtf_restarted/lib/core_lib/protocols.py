"""
core_lib.protocols — Protocol definitions for the plan-execute architecture.

Uses typing.Protocol for structural subtyping — no ABC inheritance required.
Implementations satisfy the protocol by having the right method signatures.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Plan


@runtime_checkable
class PlanRenderer(Protocol):
    """Protocol for rendering a plan to the user.

    Implementations must provide a render() method. The output_manager
    parameter is optional — renderers that don't need THAC0 integration
    can ignore it (accepts None).

    Usage:
        class MyRenderer:
            def render(self, plan: Plan, output_manager=None) -> None:
                for action in plan.actions:
                    print(f"  {action.operation}: {action.target}")

        renderer: PlanRenderer = MyRenderer()  # structural match
    """

    def render(self, plan: Plan, output_manager=None) -> None:
        """Render a plan for user review.

        Args:
            plan: The plan to display.
            output_manager: Optional OutputManager for THAC0 verbosity
                integration. None means print to stdout directly.
        """
        ...
