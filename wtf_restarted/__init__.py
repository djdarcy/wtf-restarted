"""
wtf-restarted - Why did my Windows PC restart? One command, instant answers.

Diagnoses the last Windows restart/crash by analyzing event logs, crash dumps,
and system state. Provides a plain-language verdict with actionable suggestions.

Usage:
    wtf-restarted              # Why did my PC restart?
    wtf-restarted history      # Show restart history
    wtf-restarted --ai         # AI-enhanced diagnosis
"""

from ._version import __version__, get_version, get_base_version, VERSION, BASE_VERSION

__all__ = [
    "__version__",
    "get_version",
    "get_base_version",
    "VERSION",
    "BASE_VERSION",
]
