"""Rich console rendering for wtf-restarted diagnosis results."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Verdict type → color and emoji (emoji only used in verdict box)
VERDICT_STYLES = {
    "BSOD": ("red", "BLUE SCREEN (BSOD)"),
    "UNEXPECTED_SHUTDOWN": ("yellow", "UNEXPECTED SHUTDOWN"),
    "INITIATED_RESTART": ("cyan", "INITIATED RESTART"),
    "MIXED_SIGNALS": ("magenta", "MIXED SIGNALS"),
    "CLEAN_RESTART": ("green", "CLEAN RESTART"),
    "UNKNOWN": ("white", "UNKNOWN"),
}


def render_diagnosis(data: dict, verbose: bool = False):
    """Render full diagnosis results to the console."""
    system = data.get("system", {})
    rdp = data.get("rdp", {})
    verdict = data.get("verdict", {})
    evidence = data.get("evidence", {})
    events = data.get("events", {})
    dumps = data.get("dumps", {})
    dump_analysis = data.get("dump_analysis", {})
    previous_boot = data.get("previous_boot", {})

    # Header
    console.print()
    console.print(Panel.fit(
        "[bold]WTF-RESTARTED[/bold] — Last Restart Analysis",
        style="blue",
    ))

    # System info
    _render_system_info(system, previous_boot)

    # RDP warning
    if rdp.get("is_rdp") and rdp.get("warning"):
        console.print()
        console.print(Panel(
            rdp["warning"],
            title="RDP Session Detected",
            style="yellow",
        ))
        if rdp.get("disconnected_sessions"):
            for sess in rdp["disconnected_sessions"]:
                console.print(f"  Disconnected session: {sess}", style="yellow")

    # Verdict
    console.print()
    _render_verdict(verdict, dump_analysis)

    # Evidence summary
    _render_evidence(evidence)

    # Event details (verbose or key events)
    if verbose:
        _render_all_events(events)
    else:
        _render_key_events(events)

    # Dump analysis
    if dump_analysis.get("performed"):
        _render_dump_analysis(dump_analysis)
    elif dumps.get("memory_dmp") and not dump_analysis.get("kd_available"):
        console.print()
        console.print(
            "[dim]Crash dump exists but kd.exe not found. "
            "Install Windows SDK Debugging Tools for dump analysis.[/dim]"
        )

    # Context window
    context = events.get("context_window", [])
    if context:
        _render_context_window(context)

    console.print()


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
    """Render evidence summary."""
    table = Table(title="Evidence Summary", show_header=True, header_style="bold")
    table.add_column("Check", width=30)
    table.add_column("Result", width=15)

    checks = [
        ("Dirty shutdown (Event 41/6008)", evidence.get("dirty_shutdown")),
        ("BugCheck / BSOD event", evidence.get("bugcheck")),
        ("Shutdown initiator (Event 1074)", evidence.get("initiated_by") is not None),
        ("WHEA hardware error", evidence.get("whea_error")),
        ("Windows Update near restart", evidence.get("windows_update")),
        ("Crash dump exists", evidence.get("crash_dump_exists")),
    ]

    for name, found in checks:
        if found:
            table.add_row(name, "[bold red]YES[/bold red]")
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


def render_ai_analysis(sections: dict):
    """Render AI analysis results as a Rich panel."""
    console.print()

    if "raw" in sections:
        # Unstructured response -- display as-is
        console.print(Panel(
            sections["raw"],
            title="AI Analysis",
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
            title="AI Analysis",
            border_style="bright_blue",
        ))
    else:
        console.print("[dim]AI analysis returned no structured content.[/dim]")

    console.print()


def render_history(history: list, days: int = 30):
    """Render restart history timeline."""
    console.print()
    console.print(Panel.fit(
        f"[bold]Restart History[/bold] — Last {days} days",
        style="blue",
    ))

    if not history:
        console.print("  No restart events found in the last {days} days.")
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
        msg = entry.get("message", "")[:200]

        table.add_row(
            time,
            Text(etype, style=style),
            msg,
        )

    console.print(table)
    console.print(f"\n  Total events: {len(history)}")
