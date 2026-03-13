"""
Formatters for different help output styles.
"""

from typing import List
from .core import HelpContent


class ExampleFormatter:
    """Formats help content as examples."""

    @staticmethod
    def format(item: HelpContent, prog: str = 'app', width: int = 80, **kwargs) -> str:
        """
        Format as an example line.

        Args:
            item: The help content item
            prog: Program name
            width: Target width for alignment
            **kwargs: Additional variables

        Returns:
            Formatted example with aligned comment
        """
        return item.format_as_example(prog, width, **kwargs)

    @staticmethod
    def format_list(items: List[HelpContent],
                   prog: str = 'app',
                   indent: str = "  ",
                   width: int = 80) -> List[str]:
        """
        Format a list of items as examples.

        Args:
            items: List of help content items
            prog: Program name
            indent: Indentation string
            width: Target width for alignment

        Returns:
            List of formatted lines
        """
        lines = []
        for item in items:
            example = item.format_as_example(prog, width - len(indent))
            lines.append(f"{indent}{example}")
        return lines


class TipFormatter:
    """Formats help content as tips."""

    @staticmethod
    def format(item: HelpContent, prog: str = 'app', **kwargs) -> str:
        """
        Format as a tip.

        Args:
            item: The help content item
            prog: Program name
            **kwargs: Additional variables

        Returns:
            Formatted tip string
        """
        return item.format_as_tip(prog, **kwargs)

    @staticmethod
    def format_list(items: List[HelpContent],
                   prog: str = 'app',
                   prefix: str = "TIP: ") -> List[str]:
        """
        Format a list of items as tips.

        Args:
            items: List of help content items
            prog: Program name
            prefix: Tip prefix

        Returns:
            List of formatted tip lines
        """
        lines = []
        for item in items:
            tip = item.format_as_tip(prog)
            lines.append(tip)
        return lines


class CompactFormatter:
    """Formats help content in compact form (no descriptions)."""

    @staticmethod
    def format(item: HelpContent, prog: str = 'app', **kwargs) -> str:
        """
        Format as compact command only.

        Args:
            item: The help content item
            prog: Program name
            **kwargs: Additional variables

        Returns:
            Just the command without description
        """
        return item.get_command(prog, **kwargs)

    @staticmethod
    def format_list(items: List[HelpContent],
                   prog: str = 'app',
                   indent: str = "  ") -> List[str]:
        """
        Format a list as compact commands.

        Args:
            items: List of help content items
            prog: Program name
            indent: Indentation string

        Returns:
            List of command lines
        """
        lines = []
        for item in items:
            cmd = item.get_command(prog)
            lines.append(f"{indent}{cmd}")
        return lines


class TutorialFormatter:
    """Formats help content as tutorial steps."""

    @staticmethod
    def format(item: HelpContent, prog: str = 'app', **kwargs) -> str:
        """
        Format as a tutorial step.

        Args:
            item: The help content item
            prog: Program name
            **kwargs: Additional variables

        Returns:
            Tutorial-style explanation
        """
        cmd = item.get_command(prog, **kwargs)
        return f"To {item.description.lower()}, run:\n  {cmd}"

    @staticmethod
    def format_list(items: List[HelpContent],
                   prog: str = 'app',
                   numbered: bool = True) -> List[str]:
        """
        Format a list as tutorial steps.

        Args:
            items: List of help content items
            prog: Program name
            numbered: Whether to number the steps

        Returns:
            List of tutorial lines
        """
        lines = []
        for i, item in enumerate(items, 1):
            cmd = item.get_command(prog)
            if numbered:
                lines.append(f"{i}. {item.description}:")
            else:
                lines.append(f"{item.description}:")
            lines.append(f"   {cmd}")
            lines.append("")  # Blank line between steps
        return lines
