"""
Central content registry that collects help items from all sections.

This aggregates content defined in section files and provides
a unified interface to access all help content.
"""

from typing import Dict, Optional
from .core import HelpContent


# Registry that will be populated from section files
HELP_CONTENT: Dict[str, HelpContent] = {}


def register_content(content: HelpContent) -> None:
    """Register a help content item in the global registry.

    Args:
        content: The HelpContent item to register
    """
    if content.id in HELP_CONTENT:
        raise ValueError(f"Duplicate help content ID: {content.id}")
    HELP_CONTENT[content.id] = content


def register_section_content(items: Dict[str, HelpContent]) -> None:
    """Register multiple help content items from a section.

    Args:
        items: Dictionary of content items to register
    """
    for content in items.values():
        register_content(content)


def get_content_by_id(content_id: str) -> Optional[HelpContent]:
    """Get a specific help content item by ID.

    Args:
        content_id: The unique ID of the content item

    Returns:
        The HelpContent item

    Raises:
        KeyError: If content_id doesn't exist
    """
    if content_id not in HELP_CONTENT:
        raise KeyError(f"Help content '{content_id}' not found in registry")
    return HELP_CONTENT[content_id]


def get_content_by_category(category: str) -> list:
    """Get all help content items in a category.

    Args:
        category: The category name

    Returns:
        List of HelpContent items in that category
    """
    return [
        content for content in HELP_CONTENT.values()
        if content.category == category
    ]


def get_content_by_context(context: str) -> list:
    """Get all help content items for a specific context.

    Args:
        context: The context name (e.g., 'minimal', 'standard', 'full')

    Returns:
        List of HelpContent items that include that context
    """
    return [
        content for content in HELP_CONTENT.values()
        if context in content.contexts
    ]


def get_all_content() -> Dict[str, HelpContent]:
    """Get the complete content registry.

    Returns:
        Dictionary of all HelpContent items
    """
    return HELP_CONTENT.copy()
