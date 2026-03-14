"""
OutputManager — the THAC0 verbosity system core.

Central coordinator for verbosity-gated output with per-channel overrides.
The emit rule is: message shows when message.level <= threshold.
The threshold is either a per-channel override or the global verbosity.

THAC0 axis:
    ←── quieter ────────── default ────────── louder ──→
    -4    -3     -2     -1     0     1      2      3
    wall  errors warnings minimal default timing config debug

    -v increments, -Q decrements. They compose: -vv -Q = 1

Per-channel overrides:
    --show timing:2    pins timing channel to threshold 2
    Specific > generic, except at -4 (hard wall, nothing at all)

Issue refs: #31 (multi-level verbosity), #57 (structured hints),
            #65 (named channels, THAC0 model)
"""

import sys
from typing import Any, Dict, Optional, Set, TextIO

from .hints import get_hint
from .channels import parse_channel_spec, OPT_IN_CHANNELS


class OutputManager:
    """Central coordinator for THAC0 verbosity-gated output.

    All output is written to the configured file handle (default: stderr).
    The manager tracks which hints have been shown to avoid repetition
    within a single session.

    Usage::

        out = OutputManager(verbosity=1)
        out.emit(1, "Loaded {count} items", channel='config', count=42)
        out.hint('module.some_hint', 'result', var="value")
        out.progress(100, 3.2)
        out.error("Something went wrong")
    """

    def __init__(
        self,
        verbosity: int = 0,
        channel_overrides: Dict[str, int] = None,
        file: TextIO = None,
        quiet: bool = False,
        renderer=None,
        channel_renderers: Dict[str, Any] = None,
        known_channels: Set[str] = None,
        strict_channels: bool = False,
    ):
        # Backward compat: quiet=True forces verbosity negative
        if quiet and verbosity >= 0:
            verbosity = -1
        self.verbosity = verbosity
        self.channel_overrides: Dict[str, int] = dict(channel_overrides or {})
        self.file = file if file is not None else sys.stderr
        self.channel_fds: Dict[str, TextIO] = {}
        self._shown_hints: Set[str] = set()

        # Phase 3: renderer resolution layers
        self.default_renderer = renderer
        self.channel_renderers: Dict[str, Any] = dict(channel_renderers or {})
        self.known_channels: Set[str] = set(known_channels) if known_channels else set()
        self.strict_channels = strict_channels

    def set_channel_fd(self, channel: str, fd: TextIO) -> None:
        """Set the output file handle for a channel at runtime.

        Commands can call this to redirect a channel's output for
        the duration of their execution. This overrides the channel's
        default fd from ChannelConfig but is itself overridden by the
        per-message ``file=`` parameter on emit().

        FD resolution order (highest priority first):
            1. file= on emit() call (per-message)
            2. set_channel_fd() (runtime command override)
            3. ChannelConfig.fd (channel default from channels.py)
            4. self.file (manager default — stderr)

        Args:
            channel: Channel name
            fd: File handle (e.g., sys.stdout, sys.stderr)
        """
        self.channel_fds[channel] = fd

    def _resolve_fd(self, channel: str, file: TextIO = None) -> TextIO:
        """Resolve the output file handle for a message.

        4-layer resolution: file= > channel_fds > ChannelConfig.fd > self.file

        String sentinels 'stdout' and 'stderr' are resolved to the current
        sys.stdout/sys.stderr at call time (not at init time), which is
        necessary for test frameworks that replace these at runtime.
        """
        if file is not None:
            return file
        fd = self.channel_fds.get(channel)
        if fd is None:
            return self.file
        if fd == 'stdout':
            return sys.stdout
        if fd == 'stderr':
            return sys.stderr
        return fd

    def emit(self, level: int, message: str = None, *,
             channel: str = 'general', file: TextIO = None,
             render=None, **kwargs: Any) -> bool:
        """Emit a message if level <= threshold for that channel.

        The threshold is the per-channel override if set, otherwise
        the global verbosity. At threshold -4 (hard wall), nothing
        is emitted regardless of level.

        Renderer resolution (highest priority first):
            1. render= callable on this call
            2. Per-channel renderer (channel_renderers)
            3. Global default_renderer
            4. Built-in print() fallback

        Args:
            level: Message level (higher = more verbose)
            message: Format string (uses str.format with kwargs).
                Optional when render= is provided.
            channel: Output channel name
            file: Per-message output override (highest priority FD)
            render: Callable to invoke instead of print. Called with
                no arguments -- use a closure to pass data.
            **kwargs: Values for template placeholders

        Returns:
            True if the message was shown, False if gated.
        """
        threshold = self.channel_overrides.get(channel, self.verbosity)
        if threshold <= -4:
            return False
        if level > threshold:
            return False

        # Strict channel validation
        if self.strict_channels and self.known_channels and channel not in self.known_channels:
            raise ValueError(f"Unknown channel '{channel}'")

        # Layer 1: per-call render callable
        if render is not None:
            render()
            return True

        # Layer 2: per-channel renderer
        channel_renderer = self.channel_renderers.get(channel)
        if channel_renderer is not None:
            channel_renderer()
            return True

        # Layer 3: global default renderer
        if self.default_renderer is not None:
            if message is not None:
                text = message.format(**kwargs) if kwargs else message
                self.default_renderer(text)
            return True

        # Layer 4: built-in fallback
        if message is not None and not isinstance(message, str):
            raise TypeError(
                f"emit() message must be str, got {type(message).__name__}. "
                "Use render= for complex objects."
            )
        if message is None:
            return True
        text = message.format(**kwargs) if kwargs else message
        dest = self._resolve_fd(channel, file)
        print(text, file=dest)
        return True

    def hint(self, hint_id: str, context: str = 'result', **kwargs: Any) -> None:
        """Show a hint if appropriate for context, level, and not yet shown.

        Two filters apply:
        1. Context filter: Is this hint relevant now? ('error', 'result', 'verbose')
        2. Level filter: Delegated to emit() via THAC0 threshold check.

        Args:
            hint_id: Registry key for the hint
            context: Current context ('error', 'result', 'verbose')
            **kwargs: Values for template placeholders in hint message
        """
        if hint_id in self._shown_hints:
            return
        h = get_hint(hint_id)
        if h is None:
            return
        if context not in h.context:
            return

        # Build the text before checking threshold (needed for dedup tracking)
        text = h.message.format(**kwargs) if kwargs else h.message

        # Level check via THAC0 threshold
        threshold = self.channel_overrides.get('hint', self.verbosity)
        if threshold <= -4:
            return
        if h.min_level > threshold:
            return

        dest = self._resolve_fd('hint')
        print(text, file=dest)
        self._shown_hints.add(hint_id)

    def progress(self, count: int, elapsed: float) -> None:
        """Emit a progress update (level 1, progress channel)."""
        self.emit(1, "  ... {count} results ({elapsed:.1f}s)",
                  channel='progress', count=count, elapsed=elapsed)

    def error(self, message: str, *, file: TextIO = None) -> None:
        """Emit an error message (level -3, shown unless at hard wall).

        In the THAC0 model, errors are just emit(-3, ...). They show
        at any verbosity >= -3 (i.e., everything except -QQQQ).

        Args:
            message: Error message text
            file: Per-message output override
        """
        self.emit(-3, message, channel='error', file=file)

    def is_level_active(self, level: int, channel: str = 'general') -> bool:
        """Check if a message at the given level/channel would be shown.

        Allows callers to gate expensive data collection (not just rendering)
        before calling emit(). Generalizes channel_active() to any level.

        Args:
            level: Message level to check
            channel: Channel name

        Returns:
            True if the message would pass the threshold check
        """
        threshold = self.channel_overrides.get(channel, self.verbosity)
        return threshold > -4 and level <= threshold

    def channel_active(self, channel: str) -> bool:
        """Check if a channel would display messages at its default level.

        Returns True if a level-0 message on this channel would be shown.
        Used by callers to gate expensive operations (e.g., vals capture).

        Args:
            channel: Channel name to check

        Returns:
            True if the channel is active
        """
        return self.is_level_active(0, channel)

    @property
    def quiet(self) -> bool:
        """Backward compat: True when verbosity is negative."""
        return self.verbosity < 0

    @property
    def shown_hints(self) -> Set[str]:
        """Set of hint IDs that have been displayed this session."""
        return self._shown_hints.copy()


# =============================================================================
# Module-level singleton
# =============================================================================

_manager: Optional[OutputManager] = None


def init_output(verbosity: int = 0, quiet: bool = False,
                channels: list = None,
                channel_fds: Dict[str, TextIO] = None,
                renderer=None,
                known_channels: Set[str] = None,
                strict_channels: bool = False) -> OutputManager:
    """Initialize the module-level OutputManager singleton.

    Call once at program startup after parsing CLI arguments.

    Args:
        verbosity: THAC0 verbosity level (0=default, positive=verbose, negative=quiet)
        quiet: Legacy backward compat -- if True, sets verbosity to min(verbosity, -1)
        channels: List of channel spec strings (e.g., ['timing:2', 'vals'])
        channel_fds: Default output FDs per channel (e.g., {'general': sys.stdout}).
            These populate the manager's channel_fds dict, acting as layer 3
            in the FD resolution hierarchy (below file= and set_channel_fd).
        renderer: Default renderer callable (e.g., console.print). Used as
            Layer 3 in renderer resolution when no per-call render= or
            per-channel renderer is set.
        known_channels: Set of valid channel names. When combined with
            strict_channels=True, emit() raises ValueError on unknown channels.
        strict_channels: If True, validate channel names against known_channels.

    Returns:
        The initialized OutputManager instance
    """
    global _manager

    # Backward compat: quiet=True means at least -1
    if quiet and verbosity >= 0:
        verbosity = -1

    # Apply opt-in channel defaults (off unless explicitly enabled)
    channel_overrides = {ch: -1 for ch in OPT_IN_CHANNELS}

    # Parse explicit channel specs (override opt-in defaults)
    if channels:
        for spec in channels:
            cfg = parse_channel_spec(spec)
            channel_overrides[cfg.name] = cfg.level

    _manager = OutputManager(
        verbosity=verbosity,
        channel_overrides=channel_overrides,
        renderer=renderer,
        known_channels=known_channels,
        strict_channels=strict_channels,
    )

    # Apply channel FD defaults
    if channel_fds:
        for ch, fd in channel_fds.items():
            _manager.channel_fds[ch] = fd

    return _manager


def get_output() -> OutputManager:
    """Get the module-level OutputManager, creating a default if needed."""
    global _manager
    if _manager is None:
        _manager = OutputManager()
    return _manager
