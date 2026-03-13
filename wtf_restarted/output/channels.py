"""wtf-restarted channel definitions for the THAC0 verbosity system.

This module defines the project-specific output channels. The THAC0 library
itself (wtf_restarted.lib.log_lib) is project-agnostic; channel names and
descriptions are registered here at the application layer.
"""

# Channels for wtf-restarted output domains
CHANNELS = {
    'verdict',      # Verdict determination and display
    'evidence',     # Evidence collection and summary
    'events',       # Event log entries (41, 6008, 1074, etc.)
    'dump',         # Crash dump analysis (kd.exe output)
    'context',      # Surrounding event context window
    'system',       # System info (boot time, uptime, RDP)
    'history',      # Restart history timeline
    'ai',           # AI analysis progress and results
    'progress',     # Progress indicators
    'hint',         # Contextual tips and suggestions
    'error',        # Error messages
    'trace',        # Function tracing
    'general',      # Default channel
}

CHANNEL_DESCRIPTIONS = {
    'verdict':   'Verdict determination and display',
    'evidence':  'Evidence collection and summary table',
    'events':    'Event log entries and key events',
    'dump':      'Crash dump analysis details',
    'context':   'Surrounding event context window',
    'system':    'System info (boot time, uptime, RDP)',
    'history':   'Restart history timeline',
    'ai':        'AI analysis progress and results',
    'progress':  'Progress indicators',
    'hint':      'Contextual tips and suggestions',
    'error':     'Error messages',
    'trace':     'Function call tracing',
    'general':   'General output',
}

# Channels off by default (require explicit enable)
OPT_IN_CHANNELS = {
    'trace',    # Function call tracing -- opt-in (verbose debug output)
}
