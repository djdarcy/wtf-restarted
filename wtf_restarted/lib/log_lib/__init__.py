"""
log_lib — THAC0 verbosity system with named channels.

A reusable output management library providing:
- Single-axis THAC0 verbosity (level <= threshold)
- Named output channels with per-channel overrides
- Hint registry with context filtering and dedup
- Function tracing decorator

Public API:
    OutputManager    — central coordinator
    init_output      — singleton initialization
    get_output       — access singleton
    Hint             — hint dataclass
    register_hint    — register a hint
    register_hints   — register multiple hints
    get_hint         — look up hint by ID
    ChannelConfig    — channel configuration
    parse_channel_spec — parse CLI channel spec
    KNOWN_CHANNELS   — set of recognized channel names
    trace            — function tracing decorator
"""

from .manager import OutputManager, init_output, get_output
from .hints import (
    Hint, register_hint, register_hints, get_hint, get_hints_by_category,
)
from .channels import (
    ChannelConfig, parse_channel_spec, KNOWN_CHANNELS,
    CHANNEL_DESCRIPTIONS, OPT_IN_CHANNELS, format_channel_list,
)
from .trace import trace

__all__ = [
    'OutputManager', 'init_output', 'get_output',
    'Hint', 'register_hint', 'register_hints', 'get_hint', 'get_hints_by_category',
    'ChannelConfig', 'parse_channel_spec', 'KNOWN_CHANNELS',
    'CHANNEL_DESCRIPTIONS', 'format_channel_list',
    'trace',
]
