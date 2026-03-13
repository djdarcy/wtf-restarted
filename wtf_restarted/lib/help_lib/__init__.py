"""
Universal help system for CLI applications.

This module provides a reusable help system that separates content from presentation,
allowing the same help content to be displayed as examples, tips, or in different contexts.
"""

from .core import HelpContent, HelpSection, HelpBuilder, DetailedHelpContent
from .formatters import ExampleFormatter, TipFormatter

__all__ = [
    'HelpContent',
    'HelpSection',
    'HelpBuilder',
    'DetailedHelpContent',
    'ExampleFormatter',
    'TipFormatter',
]
