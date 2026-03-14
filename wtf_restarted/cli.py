"""
Command-line interface for wtf-restarted.

Usage:
    wtf-restarted                  # Why did my PC restart?
    wtf-restarted history          # Show restart history
    wtf-restarted history --days 30
    wtf-restarted --hours 72       # Look back 72 hours
    wtf-restarted --skip-dump      # Skip crash dump analysis
    wtf-restarted --json           # JSON output
    wtf-restarted --tier 0         # Quick answer only
    wtf-restarted --tier 1,2       # Evidence + diagnostics (paged)
    wtf-restarted --no-page        # Show all tiers without paging
    wtf-restarted --verbose        # Show expanded event details
    wtf-restarted -Q               # Less detail (-Q, -QQ, -QQQ)
    wtf-restarted --show events:2  # Pin a channel to a verbosity level
    wtf-restarted --ai             # AI-enhanced analysis (Claude)
    wtf-restarted --ai codex       # AI analysis with specific backend
    wtf-restarted --ai-only        # Show only AI analysis
    wtf-restarted --version        # Show version
"""

import argparse
import json
import sys

from ._version import __version__, get_display_version


def _init_thac0(verbosity: int, channels: list = None) -> None:
    """Initialize the THAC0 output system with project channels.

    Args:
        verbosity: Computed verbosity level (verbose - quiet).
        channels: List of --show channel specs (e.g., ['events:2', 'trace:1']).
    """
    from .lib.log_lib import init_output
    from .lib.log_lib.channels import KNOWN_CHANNELS, CHANNEL_DESCRIPTIONS, OPT_IN_CHANNELS
    from .output.channels import (
        CHANNELS as APP_CHANNELS,
        CHANNEL_DESCRIPTIONS as APP_DESCRIPTIONS,
        OPT_IN_CHANNELS as APP_OPT_IN,
    )

    # Patch library-level channel registry with app-specific channels
    KNOWN_CHANNELS.clear()
    KNOWN_CHANNELS.update(APP_CHANNELS)
    CHANNEL_DESCRIPTIONS.clear()
    CHANNEL_DESCRIPTIONS.update(APP_DESCRIPTIONS)
    OPT_IN_CHANNELS.clear()
    OPT_IN_CHANNELS.update(APP_OPT_IN)

    init_output(
        verbosity=verbosity,
        channels=channels,
        known_channels=APP_CHANNELS,
        strict_channels=True,
    )


def _hours_explicit(argv) -> bool:
    """Check if --hours/-H was explicitly passed on the command line."""
    check = argv if argv is not None else sys.argv[1:]
    return any(a in ("--hours", "-H") or a.startswith("--hours=") for a in check)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        prog="wtf-restarted",
        description=(
            "Why did my Windows PC restart? "
            "Analyzes event logs, crash dumps, and system state "
            "to tell you what happened."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  wtf-restarted                     # diagnose last restart\n"
            "  wtf-restarted history             # show restart timeline\n"
            "  wtf-restarted history --days 30   # last 30 days\n"
            "  wtf-restarted --hours 72          # look back 72 hours\n"
            "  wtf-restarted --tier 0            # quick answer only\n"
            "  wtf-restarted --tier 1,2          # evidence + diagnostics\n"
            "  wtf-restarted --no-page           # all tiers, no paging\n"
            "  wtf-restarted -Q                  # less detail\n"
            "  wtf-restarted --show events:2     # pin channel verbosity\n"
            "  wtf-restarted --json              # machine-readable output\n"
        ),
    )

    p.add_argument(
        "command",
        nargs="?",
        default="diagnose",
        choices=["diagnose", "history"],
        help="command to run (default: diagnose)",
    )

    # -- Diagnosis options --
    diag = p.add_argument_group("diagnosis")
    diag.add_argument(
        "--hours", "-H",
        type=int,
        default=48,
        metavar="N",
        help="hours to look back in event logs (default: 48, auto-extends to cover last restart; explicit value = strict window)",
    )
    diag.add_argument(
        "--skip-dump",
        action="store_true",
        help="skip crash dump analysis (faster)",
    )
    diag.add_argument(
        "--context-minutes",
        type=int,
        default=10,
        metavar="N",
        help="minutes of surrounding events to show before restart (default: 10)",
    )

    # -- History options --
    hist = p.add_argument_group("history")
    hist.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        metavar="N",
        help="days of restart history to show (default: 30)",
    )

    # -- Output options --
    out = p.add_argument_group("output")
    out.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="output raw JSON instead of formatted text",
    )
    out.add_argument(
        "--tier", "-t",
        default=None,
        metavar="TIERS",
        help=(
            "tiers to show: 0=answer, 1=evidence, 2=diagnostics "
            "(comma-separated, e.g. 0,1; default: all with paging)"
        ),
    )
    out.add_argument(
        "--no-page", "-np",
        action="store_true",
        dest="no_page",
        help="disable interactive paging between tiers",
    )
    out.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="increase output detail (-v, -vv, -vvv)",
    )
    out.add_argument(
        "--quiet", "-Q",
        action="count",
        default=0,
        help="decrease output detail (-Q, -QQ, -QQQ; -QQQQ = silent)",
    )
    out.add_argument(
        "--show",
        action="append",
        default=None,
        metavar="CHANNEL:LEVEL",
        help="pin a channel to a verbosity level (e.g. events:2, trace:1)",
    )

    # -- AI options --
    ai = p.add_argument_group("ai analysis")
    ai.add_argument(
        "--ai",
        nargs="?",
        const="claude",
        default=None,
        metavar="BACKEND",
        help="enable AI analysis (backends: claude, codex, prompt-only; default: claude)",
    )
    ai.add_argument(
        "--ai-only",
        nargs="?",
        const="claude",
        default=None,
        metavar="BACKEND",
        help="show only AI analysis, skip standard output (default backend: claude)",
    )
    ai.add_argument(
        "--ai-verbose",
        action="store_true",
        help="stream AI response in real-time",
    )
    ai.add_argument(
        "--ai-refresh",
        action="store_true",
        help="force fresh AI analysis (ignore cache)",
    )

    # -- Info --
    info = p.add_argument_group("info")
    info.add_argument(
        "--version", "-V",
        action="version",
        version=f"wtf-restarted {get_display_version()} ({__version__})",
    )

    return p


def parse_tier_spec(spec: str | None) -> list[int] | None:
    """Parse --tier argument into a list of tier numbers.

    Returns None if no --tier was specified (show all tiers).
    Returns a sorted list of unique tier numbers (0, 1, 2) otherwise.
    Raises ValueError for invalid input.
    """
    if spec is None:
        return None
    spec = spec.strip()
    if spec.lower() == "all":
        return None  # all tiers = default behavior
    parts = [p.strip() for p in spec.split(",")]
    tiers = set()
    for part in parts:
        try:
            t = int(part)
        except ValueError:
            raise ValueError(
                f"invalid tier '{part}': must be 0, 1, 2, or 'all'"
            )
        if t not in (0, 1, 2):
            raise ValueError(
                f"invalid tier {t}: must be 0, 1, or 2"
            )
        tiers.add(t)
    return sorted(tiers)


def main(argv=None):
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Compute verbosity: -v increments, -Q decrements. They compose: -vv -Q = 1
    args.verbose = args.verbose - args.quiet

    # Initialize THAC0 output system
    _init_thac0(args.verbose, channels=args.show)

    # Parse --tier early so we can fail fast on bad input
    if hasattr(args, "tier") and args.tier is not None:
        try:
            args.tiers = parse_tier_spec(args.tier)
        except ValueError as e:
            parser.error(str(e))
    else:
        args.tiers = None

    if args.command == "history":
        _cmd_history(args)
    else:
        _cmd_diagnose(args, argv)


def _cmd_diagnose(args, argv=None):
    """Run full restart diagnosis."""
    from .engine.investigator import run_investigation, check_elevation
    from .output import render

    # --ai-only implies --ai with the specified (or default) backend
    if args.ai_only is not None:
        if not args.ai:
            args.ai = args.ai_only

    # Check admin privileges
    is_admin = check_elevation()
    if not is_admin:
        print(
            "WARNING: Not running as Administrator. "
            "Some event logs and crash dumps may not be accessible.\n"
            "For best results, run from an elevated terminal.\n",
            file=sys.stderr,
        )

    # Detect if --hours was explicitly passed (vs using the default).
    # Explicit --hours means strict time-slice; default means boot-anchored.
    hours_explicit = _hours_explicit(argv)

    # Run investigation (with spinner for interactive terminals)
    interactive = sys.stdout.isatty() and not args.json_output
    if interactive:
        from rich.console import Console
        from .output.spinners import register_spinners, DEFAULT_SPINNER
        register_spinners()
        console = Console(stderr=True)
        with console.status("[bold blue]Reading event logs...[/bold blue]", spinner=DEFAULT_SPINNER):
            results = run_investigation(
                lookback_hours=args.hours,
                strict_lookback=hours_explicit,
                skip_dump=args.skip_dump,
                context_minutes=args.context_minutes,
                verbose=args.verbose,
            )
    else:
        results = run_investigation(
            lookback_hours=args.hours,
            strict_lookback=hours_explicit,
            skip_dump=args.skip_dump,
            context_minutes=args.context_minutes,
            verbose=args.verbose,
        )

    if "error" in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        if results.get("stderr"):
            print(f"Details: {results['stderr']}", file=sys.stderr)
        sys.exit(1)

    # Show lookback notification -- in Tier 0 when rendered, stderr otherwise.
    # Tier 0 handles its own note via render._render_lookback_note().
    tier0_shown = args.tiers is None or 0 in args.tiers
    if not args.json_output and not tier0_shown:
        _show_lookback_note(results, hours_explicit)

    # Build AI fetcher callback (lazy -- called after Tier 0 verdict is visible)
    ai_fetcher = None
    if args.ai:
        ai_fetcher = lambda: _get_ai_sections(args, results)

    # Standard output (unless --ai-only)
    if not args.ai_only:
        if args.json_output:
            # JSON mode: must run AI synchronously before output
            ai_result = ai_fetcher() if ai_fetcher else None
            if ai_result:
                results["ai_analysis"] = ai_result
            print(json.dumps(results, indent=2))
            return
        else:
            render.render_diagnosis(
                results,
                verbose=args.verbose,
                tiers=args.tiers,
                no_page=args.no_page,
                interactive=sys.stdout.isatty(),
                ai_fetcher=ai_fetcher,
            )
            return

    # --ai-only mode: render just the AI analysis
    if args.ai_only and ai_fetcher:
        ai_result = ai_fetcher()
        if not ai_result:
            return
        if args.json_output:
            results["ai_analysis"] = ai_result
            print(json.dumps(results, indent=2))
        elif ai_result.get("success"):
            render.render_ai_analysis(ai_result["sections"])
        else:
            _report_ai_failure(args, ai_result)


def _get_ai_sections(args, results):
    """Run AI analysis and return the result dict (does not render)."""
    from .ai.analyzer import analyze, check_available

    backend = args.ai

    # Check availability before starting
    if not check_available(backend):
        if backend == "claude":
            print(
                "\nAI analysis unavailable: Claude Code CLI not found.\n"
                "Install from https://claude.ai/claude-code\n"
                "Or use --ai prompt-only to save the prompt for manual use.",
                file=sys.stderr,
            )
        else:
            print(
                f"\nAI analysis unavailable: backend '{backend}' not found.",
                file=sys.stderr,
            )
        if args.ai_only:
            sys.exit(1)
        return None

    if not args.ai_verbose and not args.json_output:
        if args.ai_refresh:
            print("Running AI analysis (cache bypassed)...", file=sys.stderr, flush=True)
        else:
            print("Running AI analysis...", file=sys.stderr, flush=True)

    ai_result = analyze(
        results,
        backend_name=backend,
        verbose=args.ai_verbose,
        timeout=120,
        refresh=args.ai_refresh,
    )

    # Note cache hit in result for downstream consumers
    if ai_result.get("cached") and not args.ai_verbose and not args.json_output:
        print("(using cached result)", file=sys.stderr)

    return {
        "success": ai_result["success"],
        "backend": backend,
        "sections": ai_result["sections"],
        "error": ai_result["error"],
    }


def _show_lookback_note(results, hours_explicit):
    """Show informative note about lookback window behavior."""
    system = results.get("system", {})
    extended = system.get("lookback_extended", False)
    actual_hours = system.get("lookback_actual_hours")
    requested_hours = system.get("lookback_hours", 48)
    strict = system.get("strict_lookback", False)

    if extended and not strict:
        # Boot-anchored mode extended past the default window
        print(
            f"Note: No restart events in last {requested_hours}h -- "
            f"looked back {actual_hours:.0f}h to cover last restart. "
            f"Use --hours {requested_hours} for strict {requested_hours}h window.",
            file=sys.stderr,
        )
    elif strict and not extended:
        # Strict mode and boot time is inside the window -- no note needed
        pass
    elif strict:
        # Strict mode but this shouldn't happen (extended=True + strict=True
        # is contradictory since strict disables extension)
        pass

    # Check if strict mode missed the restart entirely
    if strict:
        verdict_type = results.get("verdict", {}).get("type", "")
        boot_time = system.get("boot_time", "")
        if verdict_type == "CLEAN_RESTART" and actual_hours and boot_time:
            uptime_hrs = system.get("uptime_seconds", 0) / 3600
            if uptime_hrs > requested_hours:
                print(
                    f"Note: Last restart was ~{uptime_hrs:.0f}h ago, "
                    f"outside your --hours {requested_hours} window. "
                    f"Run without --hours or use --hours {int(uptime_hrs) + 1} "
                    f"to include it.",
                    file=sys.stderr,
                )


def _report_ai_failure(args, ai_result):
    """Report AI analysis failure to stderr."""
    backend = ai_result.get("backend", args.ai)
    if backend == "prompt-only":
        print(f"\n{ai_result['error']}", file=sys.stderr)
    else:
        error = ai_result.get("error", "Unknown error")
        print(f"\nAI analysis failed: {error}", file=sys.stderr)


def _cmd_history(args):
    """Show restart history timeline."""
    from .engine.history import get_restart_history
    from .output import render

    history = get_restart_history(days=args.days)

    if args.json_output:
        print(json.dumps(history, indent=2))
    else:
        render.render_history(history, days=args.days)


if __name__ == "__main__":
    main()
