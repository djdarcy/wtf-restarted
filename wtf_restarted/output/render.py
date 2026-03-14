"""Rich console rendering for wtf-restarted diagnosis results.

Three-tier progressive disclosure (Issue #17):
  Tier 0 (Answer):      Header + system info + RDP warning + verdict + AI analysis
  Tier 1 (Evidence):    Evidence table + key events (41, 6008, shutdown initiator)
  Tier 2 (Diagnostics): BugCheck, GPU, WU, WHEA, dump analysis, context window

Output gating (Phase 3 THAC0 integration, Issue #15):
  Each render section is wrapped in emit() with a channel and level.
  -v/-Q/--show control what content populates sections.
  --tier controls which sections (template) are shown.
  -Q wins over --tier (if a channel is gated by verbosity, it's hidden
  even if the tier is selected).
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..lib.log_lib import get_output

console = Console()

# Verdict type -> color and label
VERDICT_STYLES = {
    "BSOD": ("red", "BLUE SCREEN (BSOD)"),
    "UNEXPECTED_SHUTDOWN": ("yellow", "UNEXPECTED SHUTDOWN"),
    "INITIATED_RESTART": ("cyan", "INITIATED RESTART"),
    "MIXED_SIGNALS": ("magenta", "MIXED SIGNALS"),
    "CLEAN_RESTART": ("green", "CLEAN RESTART"),
    "UNKNOWN": ("white", "UNKNOWN"),
}

# Evidence check -> severity category for color coding
_EVIDENCE_SEVERITY = {
    "dirty_shutdown": "bad",
    "bugcheck": "bad",
    "whea_error": "bad",
    "initiated_by": "info",
    "windows_update": "info",
    "crash_dump_exists": "data",
}

_SEVERITY_STYLE = {
    "bad": "bold red",
    "info": "bold cyan",
    "data": "bold green",
}


def _wait_for_keypress(prompt: str = "Press any key for more details..."):
    """Wait for a keypress in interactive mode. Returns the key pressed."""
    console.print(f"\n[dim]{prompt}[/dim]", end="")
    try:
        import msvcrt
        ch = msvcrt.getwch()
        console.print()  # newline after keypress
        # Esc key returns '\x1b'
        if ch == "\x1b":
            return "q"
        return ch
    except ImportError:
        # Non-Windows fallback
        try:
            line = input()
            if line.strip().lower() == "q":
                return "q"
            return "\n"
        except (EOFError, KeyboardInterrupt):
            return "q"


def _is_interactive():
    """Check if stdout is a TTY (not piped/redirected)."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _has_tier1_content(data: dict) -> bool:
    """Check if there is Tier 1 (evidence) content to show.

    Checks both data existence AND channel visibility (Phase 3).
    If the evidence/events channels are gated by verbosity, returns False
    even if data exists -- there's nothing to render.
    """
    out = get_output()
    evidence = data.get("evidence", {})
    events = data.get("events", {})
    if out.is_level_active(0, 'evidence') and any(evidence.get(k) for k in _EVIDENCE_SEVERITY):
        return True
    if out.is_level_active(0, 'events'):
        for key in ("kernel_power_41", "event_6008", "shutdown_initiator"):
            if events.get(key):
                return True
    return False


def _has_tier2_content(data: dict) -> bool:
    """Check if there is Tier 2 (diagnostics) content to show.

    Checks both data existence AND channel visibility (Phase 3).
    Diagnostic events are level 0, context window is level 0,
    verbose all-events is level 1.
    """
    out = get_output()
    events = data.get("events", {})
    dump_analysis = data.get("dump_analysis", {})
    dumps = data.get("dumps", {})
    if out.is_level_active(0, 'events'):
        for key in ("bugcheck", "gpu_events", "windows_update", "whea"):
            if events.get(key):
                return True
    if out.is_level_active(0, 'context'):
        if events.get("context_window"):
            return True
    if out.is_level_active(0, 'dump'):
        if dump_analysis.get("performed"):
            return True
        if dumps.get("memory_dmp") and not dump_analysis.get("kd_available"):
            return True
    return False


# ---------------------------------------------------------------------------
# Tier 0: The Answer
# ---------------------------------------------------------------------------

def _render_tier0(data: dict, ai_fetcher=None):
    """Render Tier 0: header, system info, RDP warning, verdict, AI analysis.

    AI is fetched lazily via ai_fetcher callback so the user sees the verdict
    immediately while AI analysis runs.

    Output gating (Phase 3):
      Header:      system/-2 (shown even at -QQ)
      System info: system/-1 (hidden at -QQ, shown at -Q and above)
      Lookback:    system/-1
      RDP warning: system/-2
      Verdict:     verdict/-2
      AI analysis: ai/0
    """
    out = get_output()
    system = data.get("system", {})
    rdp = data.get("rdp", {})
    verdict = data.get("verdict", {})
    dump_analysis = data.get("dump_analysis", {})
    previous_boot = data.get("previous_boot", {})

    # Header (level -2: shown even at -QQ)
    out.emit(-2, channel='system', render=lambda: (
        console.print(),
        console.print(Panel.fit(
            "[bold]WTF-RESTARTED[/bold] -- Last Restart Analysis",
            style="blue",
        )),
    ))

    # System info (level -1: hidden at -QQ, shown at -Q and above)
    out.emit(-1, channel='system', render=lambda:
        _render_system_info(system, previous_boot))

    # Lookback note (level -1: same as system info)
    out.emit(-1, channel='system', render=lambda:
        _render_lookback_note(system, data.get("verdict", {})))

    # RDP warning (level -2: shown even at -QQ)
    if rdp.get("is_rdp") and rdp.get("warning"):
        def _render_rdp():
            console.print()
            console.print(Panel(
                rdp["warning"],
                title="RDP Session Detected",
                style="yellow",
            ))
            if rdp.get("disconnected_sessions"):
                for sess in rdp["disconnected_sessions"]:
                    console.print(f"  Disconnected session: {sess}", style="yellow")
        out.emit(-2, channel='system', render=_render_rdp)

    # Verdict (level -2: shown even at -QQ)
    out.emit(-2, channel='verdict', render=lambda: (
        console.print(),
        _render_verdict(verdict, dump_analysis),
    ))

    # AI analysis (level 0: shown at default and above)
    # Fetched AFTER verdict is visible so user sees immediate output
    if ai_fetcher:
        def _fetch_and_render_ai():
            ai_result = ai_fetcher()
            if ai_result and ai_result.get("success"):
                render_ai_analysis(
                    ai_result["sections"],
                    title="AI Analysis (based on all collected evidence)",
                )
            elif ai_result and ai_result.get("error"):
                error = ai_result.get("error", "Unknown error")
                backend = ai_result.get("backend", "")
                if backend == "prompt-only":
                    print(f"\n{error}", file=sys.stderr)
                else:
                    print(f"\nAI analysis failed: {error}", file=sys.stderr)
        out.emit(0, channel='ai', render=_fetch_and_render_ai)


# ---------------------------------------------------------------------------
# Tier 1: Evidence
# ---------------------------------------------------------------------------

def _render_tier1(data: dict):
    """Render Tier 1: evidence summary table + key shutdown/crash events.

    Output gating (Phase 3):
      Evidence table: evidence/0
      Key events:     events/0
    """
    out = get_output()
    evidence = data.get("evidence", {})
    events = data.get("events", {})

    out.emit(0, channel='evidence', render=lambda:
        _render_evidence(evidence))

    # Key events that directly explain the restart
    tier1_sections = [
        ("Kernel-Power Event 41 (Unexpected Shutdown)", events.get("kernel_power_41", [])),
        ("Event 6008 (Previous Shutdown Was Unexpected)", events.get("event_6008", [])),
        ("Shutdown Initiator", events.get("shutdown_initiator", [])),
    ]

    for title, items in tier1_sections:
        if items:
            def _render_event_section(t=title, it=items):
                console.print()
                console.print(f"[bold]{t}[/bold]")
                for e in it[:5]:
                    msg = e.get("message", "")
                    time = e.get("time", "")
                    console.print(f"  [{time}] {msg}")
            out.emit(0, channel='events', render=_render_event_section)


# ---------------------------------------------------------------------------
# Tier 2: Diagnostics
# ---------------------------------------------------------------------------

def _render_tier2(data: dict, verbose: int = 0):
    """Render Tier 2: deep diagnostics (bugcheck, GPU, WU, WHEA, dumps, context).

    Output gating (Phase 3):
      Diagnostic events: events/0 (default sections)
      Verbose all-events: events/1 (shown only with -v)
      Dump analysis:     dump/0
      Context window:    context/0
    """
    out = get_output()
    events = data.get("events", {})
    dumps = data.get("dumps", {})
    dump_analysis = data.get("dump_analysis", {})

    if verbose:
        # Verbose mode: show ALL events with full detail (level 1)
        out.emit(1, channel='events', render=lambda:
            _render_all_events(events))
    else:
        # Diagnostic event sections (level 0: shown at default)
        tier2_sections = [
            ("BugCheck / BSOD Events", events.get("bugcheck", [])),
            ("GPU Driver Events (TDR/Display Recovery)", events.get("gpu_events", [])),
            ("Windows Update Events", events.get("windows_update", [])),
            ("WHEA Hardware Errors", events.get("whea", [])),
        ]

        for title, items in tier2_sections:
            if items:
                def _render_diag_section(t=title, it=items):
                    console.print()
                    console.print(f"[bold]{t}[/bold]")
                    for e in it[:5]:
                        msg = e.get("message", "")
                        time = e.get("time", "")
                        console.print(f"  [{time}] {msg}")
                out.emit(0, channel='events', render=_render_diag_section)

    # Dump analysis
    if dump_analysis.get("performed"):
        out.emit(0, channel='dump', render=lambda:
            _render_dump_analysis(dump_analysis))
    elif dumps.get("memory_dmp") and not dump_analysis.get("kd_available"):
        out.emit(0, channel='dump', render=lambda: (
            console.print(),
            console.print(
                "[dim]Crash dump exists but kd.exe not found. "
                "Install Windows SDK Debugging Tools for dump analysis.[/dim]"
            ),
        ))

    # Context window (level 0: shown at default)
    context = events.get("context_window", [])
    if context:
        out.emit(0, channel='context', render=lambda:
            _render_context_window(context))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_diagnosis(
    data: dict,
    verbose: int = 0,
    tiers: list[int] | None = None,
    no_page: bool = False,
    interactive: bool = True,
    ai_fetcher=None,
):
    """Render diagnosis results with three-tier progressive disclosure.

    Args:
        data: Investigation results dict from PowerShell engine.
        verbose: Verbosity level (0=default, positive=verbose, negative=quiet).
            Controls content within tiers via THAC0 emit() gating.
        tiers: Which tiers to show (None = all). List of 0, 1, 2.
        no_page: Disable interactive paging between tiers.
        interactive: Whether stdout is a TTY (enables keypress paging).
        ai_fetcher: Callable that returns AI analysis result dict, or None.
            Called lazily after the verdict is displayed so the user sees
            immediate output while AI runs.
    """
    # Determine which tiers to render
    show_tiers = tiers if tiers is not None else [0, 1, 2]

    # Determine whether to page between tiers
    # Page when: interactive TTY, not --no-page, multiple tiers to show
    paging = (
        interactive
        and not no_page
        and len(show_tiers) > 1
    )

    # Build list of (tier_number, render_func, prompt) tuples
    tier_renderers = []

    if 0 in show_tiers:
        tier_renderers.append((
            0,
            lambda: _render_tier0(data, ai_fetcher=ai_fetcher),
            None,  # No prompt before Tier 0
        ))

    if 1 in show_tiers and _has_tier1_content(data):
        tier_renderers.append((
            1,
            lambda: _render_tier1(data),
            "Press any key for evidence details, q/Esc to quit...",
        ))

    if 2 in show_tiers and _has_tier2_content(data):
        tier_renderers.append((
            2,
            lambda: _render_tier2(data, verbose=verbose),
            "Press any key for full diagnostics, q/Esc to quit...",
        ))

    # Render each tier, with optional paging between them
    for i, (tier_num, render_fn, prompt) in enumerate(tier_renderers):
        if paging and i > 0 and prompt:
            key = _wait_for_keypress(prompt)
            if key.lower() == "q":
                console.print()
                return
        render_fn()

    # If --ai was requested but tier 0 was excluded, render AI after the
    # last tier so the user still gets their AI analysis
    if ai_fetcher and 0 not in show_tiers:
        ai_result = ai_fetcher()
        if ai_result and ai_result.get("success"):
            render_ai_analysis(ai_result["sections"])
        elif ai_result and ai_result.get("error"):
            error = ai_result.get("error", "Unknown error")
            backend = ai_result.get("backend", "")
            if backend == "prompt-only":
                print(f"\n{error}", file=sys.stderr)
            else:
                print(f"\nAI analysis failed: {error}", file=sys.stderr)

    console.print()


# ---------------------------------------------------------------------------
# Shared rendering helpers
# ---------------------------------------------------------------------------

def _render_lookback_note(system: dict, verdict: dict):
    """Render lookback window note in Tier 0 when relevant."""
    extended = system.get("lookback_extended", False)
    actual_hours = system.get("lookback_actual_hours")
    requested_hours = system.get("lookback_hours", 48)
    strict = system.get("strict_lookback", False)

    if extended and not strict:
        console.print(
            f"  [dim]Looked back {actual_hours:.0f}h to cover last restart "
            f"(default is {requested_hours}h). "
            f"Use --hours {requested_hours} for strict window.[/dim]"
        )
    elif strict:
        verdict_type = verdict.get("type", "")
        if verdict_type == "CLEAN_RESTART" and actual_hours:
            uptime_hrs = system.get("uptime_seconds", 0) / 3600
            if uptime_hrs > requested_hours:
                console.print(
                    f"  [dim]Last restart was ~{uptime_hrs:.0f}h ago, "
                    f"outside your --hours {requested_hours} window. "
                    f"Run without --hours or use "
                    f"--hours {int(uptime_hrs) + 1} to include it.[/dim]"
                )


def _render_system_info(system: dict, previous_boot: dict):
    """Render system information table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("label", style="bold", width=18)
    table.add_column("value")

    table.add_row("Last boot:", system.get("boot_time", "unknown"))
    table.add_row("Current uptime:", system.get("uptime_display", "unknown"))
    table.add_row("Computer:", system.get("computer_name", "unknown"))

    if previous_boot.get("previous_boot"):
        table.add_row("Previous boot:", previous_boot["previous_boot"])
        table.add_row("Previous uptime:", previous_boot.get("previous_uptime", "unknown"))

    console.print(table)


def _render_verdict(verdict: dict, dump_analysis: dict):
    """Render the verdict panel."""
    vtype = verdict.get("type", "UNKNOWN")
    color, label = VERDICT_STYLES.get(vtype, ("white", vtype))

    lines = [f"[bold {color}]{label}[/bold {color}]"]
    lines.append("")
    lines.append(verdict.get("summary", ""))

    for detail in verdict.get("details", []):
        lines.append(f"  - {detail}")

    # Add dump analysis summary -- conditional on verdict type
    if dump_analysis.get("performed") and dump_analysis.get("bugcheck_code"):
        if vtype in ("BSOD", "MIXED_SIGNALS"):
            # Show bugcheck details inline for crash verdicts
            lines.append("")
            lines.append(f"Bugcheck: {dump_analysis['bugcheck_code']}")
            if dump_analysis.get("module"):
                lines.append(f"Faulting module: {dump_analysis['module']}")
            if dump_analysis.get("image"):
                lines.append(f"Driver image: {dump_analysis['image']}")
        else:
            # For non-crash verdicts, just note that a dump exists
            lines.append("")
            lines.append(
                "[dim]Note: Previous crash dump found "
                "(run 'wtfr -v' for details)[/dim]"
            )

    console.print(Panel(
        "\n".join(lines),
        title="VERDICT",
        border_style=color,
    ))


def _render_evidence(evidence: dict):
    """Render evidence summary table with severity-based colors."""
    table = Table(title="Evidence Summary", show_header=True, header_style="bold")
    table.add_column("Check", width=30)
    table.add_column("Result", width=15)

    checks = [
        ("Dirty shutdown (Event 41/6008)", evidence.get("dirty_shutdown"), "dirty_shutdown"),
        ("BugCheck / BSOD event", evidence.get("bugcheck"), "bugcheck"),
        ("Shutdown initiator (Event 1074)", evidence.get("initiated_by") is not None, "initiated_by"),
        ("WHEA hardware error", evidence.get("whea_error"), "whea_error"),
        ("Windows Update near restart", evidence.get("windows_update"), "windows_update"),
        ("Crash dump exists", evidence.get("crash_dump_exists"), "crash_dump_exists"),
    ]

    for name, found, key in checks:
        if found:
            severity = _EVIDENCE_SEVERITY.get(key, "info")
            style = _SEVERITY_STYLE.get(severity, "bold cyan")
            table.add_row(name, f"[{style}]YES[/{style}]")
        else:
            table.add_row(name, "[dim]no[/dim]")

    console.print()
    console.print(table)


def _render_key_events(events: dict):
    """Render only the most important events (non-verbose mode)."""
    sections = [
        ("Kernel-Power Event 41 (Unexpected Shutdown)", events.get("kernel_power_41", [])),
        ("Event 6008 (Previous Shutdown Was Unexpected)", events.get("event_6008", [])),
        ("Shutdown Initiator", events.get("shutdown_initiator", [])),
        ("BugCheck / BSOD Events", events.get("bugcheck", [])),
        ("GPU Driver Events (TDR/Display Recovery)", events.get("gpu_events", [])),
        ("Windows Update Events", events.get("windows_update", [])),
        ("WHEA Hardware Errors", events.get("whea", [])),
    ]

    for title, items in sections:
        if items:
            console.print()
            console.print(f"[bold]{title}[/bold]")
            for e in items[:5]:
                msg = e.get("message", "")
                time = e.get("time", "")
                console.print(f"  [{time}] {msg}")


def _render_all_events(events: dict):
    """Render all event categories (verbose mode)."""
    all_sections = [
        ("Kernel-Power Event 41", events.get("kernel_power_41", [])),
        ("Event 6008 (Dirty Shutdown)", events.get("event_6008", [])),
        ("Shutdown Initiator (1074/1076)", events.get("shutdown_initiator", [])),
        ("Power Transitions (Event 109)", events.get("power_transitions", [])),
        ("BugCheck / BSOD", events.get("bugcheck", [])),
        ("WHEA Hardware Errors", events.get("whea", [])),
        ("Windows Update", events.get("windows_update", [])),
        ("Application Crashes", events.get("app_crashes", [])),
        ("GPU Driver Events", events.get("gpu_events", [])),
        ("Boot/Shutdown Sequence", events.get("boot_sequence", [])),
    ]

    for title, items in all_sections:
        console.print()
        console.print(f"[bold]{title}[/bold]")
        if not items:
            console.print("  [dim]None found[/dim]")
        else:
            for e in items:
                time = e.get("time", "")
                eid = e.get("id", "")
                label = e.get("label", "")
                msg = e.get("message", "")
                prefix = f"[{time}]"
                if label:
                    prefix += f" {label}"
                if eid:
                    prefix += f" (ID={eid})"
                console.print(f"  {prefix} {msg}")


def _render_dump_analysis(dump_analysis: dict):
    """Render crash dump analysis results."""
    console.print()
    console.print("[bold]Crash Dump Analysis[/bold]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("field", style="bold", width=12)
    table.add_column("value")

    fields = [
        ("Dump file", dump_analysis.get("dump_file")),
        ("Bugcheck", dump_analysis.get("bugcheck_code")),
        ("Module", dump_analysis.get("module")),
        ("Image", dump_analysis.get("image")),
        ("Symbol", dump_analysis.get("symbol")),
        ("Process", dump_analysis.get("process")),
        ("Bucket", dump_analysis.get("bucket")),
    ]

    for name, value in fields:
        if value:
            table.add_row(f"{name}:", value)

    console.print(table)


def _render_context_window(context: list):
    """Render surrounding events near the restart."""
    console.print()
    console.print("[bold]Surrounding Events (before restart)[/bold]")
    for e in context[:15]:
        time = e.get("time", "")
        provider = e.get("provider", "")
        msg = e.get("message", "")
        console.print(f"  [{time}] [dim]{provider}[/dim] {msg}")


def render_ai_analysis(sections: dict, title: str = "AI Analysis"):
    """Render AI analysis results as a Rich panel.

    Note: This is called both from _render_tier0 (already gated by emit)
    and directly from cli.py for --ai-only mode. When called directly,
    it renders unconditionally (the caller handles gating).
    """
    console.print()

    if "raw" in sections:
        # Unstructured response -- display as-is
        console.print(Panel(
            sections["raw"],
            title=title,
            border_style="bright_blue",
        ))
        return

    lines = []

    if sections.get("what_happened"):
        lines.append("[bold]What Happened[/bold]")
        lines.append(sections["what_happened"])
        lines.append("")

    if sections.get("why"):
        lines.append("[bold]Why[/bold]")
        lines.append(sections["why"])
        lines.append("")

    if sections.get("what_to_do"):
        lines.append("[bold]What To Do[/bold]")
        lines.append(sections["what_to_do"])
        lines.append("")

    if sections.get("confidence"):
        confidence = sections["confidence"]
        # Color the confidence level
        if confidence.lower().startswith("high"):
            lines.append(f"[bold]Confidence:[/bold] [green]{confidence}[/green]")
        elif confidence.lower().startswith("low"):
            lines.append(f"[bold]Confidence:[/bold] [red]{confidence}[/red]")
        else:
            lines.append(f"[bold]Confidence:[/bold] [yellow]{confidence}[/yellow]")

    if lines:
        console.print(Panel(
            "\n".join(lines),
            title=title,
            border_style="bright_blue",
        ))
    else:
        console.print("[dim]AI analysis returned no structured content.[/dim]")

    console.print()


def render_history(history: list, days: int = 30):
    """Render restart history timeline.

    Output gating (Phase 3): history/0
    """
    out = get_output()

    def _render():
        console.print()
        console.print(Panel.fit(
            f"[bold]Restart History[/bold] -- Last {days} days",
            style="blue",
        ))

        if not history:
            console.print(f"  No restart events found in the last {days} days.")
            console.print("  (This likely means the system has been running continuously.)")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Date/Time", width=20)
        table.add_column("Type", width=20)
        table.add_column("Details", ratio=1)

        type_styles = {
            "START": "green",
            "CLEAN_STOP": "green",
            "DIRTY_SHUTDOWN": "red",
            "INITIATED_RESTART": "cyan",
            "BSOD": "bold red",
        }

        for entry in history:
            etype = entry.get("type", "UNKNOWN")
            style = type_styles.get(etype, "white")
            time = entry.get("time", "")
            msg = entry.get("message", "")[:200]  # bumped from 80; revisit when config file exists

            table.add_row(
                time,
                Text(etype, style=style),
                msg,
            )

        console.print(table)
        console.print(f"\n  Total events: {len(history)}")

    out.emit(0, channel='history', render=_render)
