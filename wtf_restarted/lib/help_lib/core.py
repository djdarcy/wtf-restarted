"""
Core help system components.
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional


@dataclass
class HelpContent:
    """
    A single help item that can be formatted in different ways.

    This is the atomic unit of help - a command and its description
    that can be rendered as an example, tip, or other format.
    """
    id: str                          # Unique identifier like "basic.recursive"
    command: str                     # Command template like "{prog} {path} -fa"
    description: str                 # What the command does
    category: str = 'general'       # Category for grouping
    contexts: Set[str] = field(default_factory=lambda: {'minimal', 'standard'})
    priority: int = 50               # Lower = higher priority
    variables: Dict[str, str] = field(default_factory=dict)  # Default variable values

    def get_command(self, prog: str = 'app', **kwargs) -> str:
        """
        Render the command with substitutions.

        Args:
            prog: Program name to substitute for {prog}
            **kwargs: Additional variables to substitute

        Returns:
            Formatted command string
        """
        # Start with default variables
        vars = dict(self.variables)
        vars.update(kwargs)
        vars['prog'] = prog

        # Replace all variables
        result = self.command
        for key, value in vars.items():
            result = result.replace(f'{{{key}}}', str(value))

        return result

    def format_as_example(self, prog: str = 'app', comment_column: int = 50, **kwargs) -> str:
        """
        Format as an example line with aligned comment.

        Args:
            prog: Program name
            comment_column: Column where comment should start
            **kwargs: Additional variables

        Returns:
            Formatted example like: "app file.txt -o out.txt    # Process file"
        """
        cmd = self.get_command(prog, **kwargs)
        comment = f"# {self.description}"

        # Calculate padding to reach the comment column
        padding_needed = comment_column - len(cmd)

        if padding_needed > 2:
            # Normal case - add padding to reach comment column
            return f"{cmd}{' ' * padding_needed}{comment}"
        else:
            # Command is too long, just use 2 spaces
            return f"{cmd}  {comment}"

    def format_as_tip(self, prog: str = 'app', **kwargs) -> str:
        """
        Format as a tip.

        Returns:
            Formatted tip like: "TIP: Process file recursively: app file.txt -r"
        """
        cmd = self.get_command(prog, **kwargs)
        return f"TIP: {self.description}: {cmd}"


@dataclass
class DetailedHelpContent:
    """
    A help content item that supports multiple levels of detail.

    This class extends the basic HelpContent concept to support brief,
    standard, and detailed descriptions, allowing users to choose the
    level of information they need.
    """
    id: str                          # Unique identifier like "strategy.deep"
    topic: str                       # Topic name like "strategy" or "analyze"
    brief: str                       # One-line description
    standard: str                    # Normal help text (paragraph)
    detailed: str                    # Full technical documentation
    examples: List[str] = field(default_factory=list)  # Code examples
    validation_tests: List[str] = field(default_factory=list)  # Test cases
    category: str = 'general'        # Category for grouping
    priority: int = 50               # Lower = higher priority

    def get_content(self, level: str = 'standard') -> str:
        """
        Get content at the specified detail level.

        Args:
            level: Detail level ('brief', 'standard', 'detailed')

        Returns:
            Content at the requested level
        """
        if level == 'brief':
            return self.brief
        elif level == 'detailed':
            return self.detailed
        else:  # standard
            return self.standard

    def get_formatted_content(self, level: str = 'standard', padding: str = " ") -> str:
        """
        Get formatted content with optional left padding.

        Args:
            level: Detail level ('brief', 'standard', 'detailed')
            padding: String to prepend to each line

        Returns:
            Formatted content with padding
        """
        content = self.get_content(level)

        # Add examples if detailed level
        if level == 'detailed' and self.examples:
            content += "\n\nEXAMPLES:\n" + "\n".join(self.examples)

        # Apply padding
        if padding:
            lines = content.split('\n')
            padded_lines = [padding + line if line.strip() else "" for line in lines]
            return '\n'.join(padded_lines)

        return content

    def validate_claims(self) -> Dict[str, bool]:
        """
        Validate claims made in the help content.

        Returns:
            Dict mapping validation test names to pass/fail status
        """
        results = {}
        for test in self.validation_tests:
            results[test] = True
        return results


class HelpSection:
    """
    A collection of related help content items.

    Sections group related examples and manage how they're displayed
    in different contexts.
    """

    def __init__(self, id: str, title: str):
        """
        Initialize a help section.

        Args:
            id: Unique section identifier like "basic" or "network"
            title: Display title like "Basic Examples"
        """
        self.id = id
        self.title = title
        self.items: List[HelpContent] = []

    def add_item(self, item: HelpContent):
        """Add a help content item to this section."""
        self.items.append(item)

    def add_items(self, *items: HelpContent):
        """Add multiple help content items."""
        self.items.extend(items)

    def get_items_for_context(self, context: str) -> List[HelpContent]:
        """
        Get items that should be shown in a specific context.

        Args:
            context: Context name like 'minimal' or 'standard'

        Returns:
            List of items that include this context
        """
        return [item for item in self.items if context in item.contexts]

    def get_items_by_ids(self, ids: List[str]) -> List[HelpContent]:
        """
        Get specific items by their IDs.

        Args:
            ids: List of item IDs to retrieve

        Returns:
            List of matching items
        """
        id_set = set(ids)
        return [item for item in self.items if item.id in id_set]

    def get_items_by_category(self, category: str) -> List[HelpContent]:
        """Get items in a specific category."""
        return [item for item in self.items if item.category == category]

    def format_section(self,
                      context: str = 'standard',
                      prog: str = 'app',
                      max_items: Optional[int] = None,
                      item_ids: Optional[List[str]] = None) -> str:
        """
        Format the entire section for display.

        Args:
            context: Which context to format for
            prog: Program name
            max_items: Maximum number of items to show
            item_ids: Specific item IDs to show (overrides context)

        Returns:
            Formatted section with title and examples
        """
        # Get items based on parameters
        if item_ids:
            items = self.get_items_by_ids(item_ids)
        else:
            items = self.get_items_for_context(context)

        # Sort by priority
        items.sort(key=lambda x: x.priority)

        # Apply limit
        if max_items:
            items = items[:max_items]

        if not items:
            return ""

        # Calculate the longest command to determine comment column
        # Add 2 for the indent
        max_cmd_length = 2
        for item in items:
            cmd_length = len(item.get_command(prog)) + 2  # +2 for indent
            max_cmd_length = max(max_cmd_length, cmd_length)

        # Set comment column with some padding
        comment_column = min(max_cmd_length + 2, 50)  # Cap at column 50

        # Build output
        lines = [f"{self.title}:"]
        for item in items:
            # Pass comment_column minus indent length
            example = item.format_as_example(prog, comment_column=comment_column - 2)
            lines.append(f"  {example}")

        return "\n".join(lines)


class HelpBuilder:
    """
    Builds complete help output from sections.

    This class orchestrates the help system, managing sections
    and building appropriate help for different contexts.
    """

    def __init__(self, prog: str = 'app'):
        """
        Initialize the help builder.

        Args:
            prog: Program name
        """
        self.prog = prog
        self.sections: Dict[str, HelpSection] = {}
        self.displayed_ids: Set[str] = set()  # Track what's been shown

    def add_section(self, section: HelpSection):
        """Add a section to the help system."""
        self.sections[section.id] = section

    def build_minimal_help(self,
                          section_ids: List[str] = None,
                          max_per_section: int = 3) -> str:
        """
        Build minimal help output with consistent comment alignment.

        Args:
            section_ids: Which sections to include (default: all)
            max_per_section: Maximum examples per section

        Returns:
            Formatted minimal help text
        """
        self.displayed_ids.clear()
        output = []

        sections_to_show = section_ids or list(self.sections.keys())

        # First pass: calculate the maximum command length across all sections
        max_cmd_length = 0
        for section_id in sections_to_show:
            if section_id in self.sections:
                section = self.sections[section_id]
                items = section.get_items_for_context('minimal')[:max_per_section]
                for item in items:
                    cmd_length = len(item.get_command(self.prog))
                    max_cmd_length = max(max_cmd_length, cmd_length)

        # Set global comment column (with indent)
        comment_column = min(max_cmd_length + 4, 52)  # +4 for indent and padding

        # Second pass: format sections with consistent comment column
        for section_id in sections_to_show:
            if section_id in self.sections:
                section = self.sections[section_id]
                items = section.get_items_for_context('minimal')[:max_per_section]

                if items:
                    lines = [f"{section.title}:"]
                    for item in sorted(items, key=lambda x: x.priority):
                        example = item.format_as_example(self.prog, comment_column=comment_column - 2)
                        lines.append(f"  {example}")
                        self.displayed_ids.add(item.id)

                    output.append("\n".join(lines))

        return "\n\n".join(output)

    def build_standard_help(self) -> str:
        """
        Build standard (full) help output.

        Returns:
            Formatted standard help text
        """
        self.displayed_ids.clear()
        output = []

        for section in self.sections.values():
            section_text = section.format_section(
                context='standard',
                prog=self.prog
            )
            if section_text:
                output.append(section_text)
                # Track displayed items
                for item in section.get_items_for_context('standard'):
                    self.displayed_ids.add(item.id)

        return "\n\n".join(output)

    def get_random_tip(self, exclude_displayed: bool = True) -> str:
        """
        Get a random tip from non-displayed content.

        Args:
            exclude_displayed: Whether to exclude already displayed items

        Returns:
            Formatted tip string or empty string
        """
        import random

        # Collect all items
        all_items = []
        for section in self.sections.values():
            all_items.extend(section.items)

        # Filter out displayed if requested
        if exclude_displayed:
            available = [item for item in all_items
                        if item.id not in self.displayed_ids]
        else:
            available = all_items

        if not available:
            return ""

        # Pick random item
        item = random.choice(available)
        self.displayed_ids.add(item.id)

        return item.format_as_tip(self.prog)
