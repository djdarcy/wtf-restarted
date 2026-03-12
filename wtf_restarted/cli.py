"""
Command-line interface for wtf-restarted.

Usage:
    wtf-restarted                  # Why did my PC restart?
    wtf-restarted history          # Show restart history
    wtf-restarted history --days 30
    wtf-restarted --hours 72       # Look back 72 hours
    wtf-restarted --skip-dump      # Skip crash dump analysis
    wtf-restarted --json           # JSON output
    wtf-restarted --verbose        # Show raw event details
    wtf-restarted --ai             # AI-enhanced analysis (Claude)
    wtf-restarted --ai codex       # AI analysis with specific backend
    wtf-restarted --ai-only        # Show only AI analysis
    wtf-restarted --version        # Show version
"""

import argparse
import json
import sys

from ._version import __version__, get_display_version


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
            "  wtf-restarted --skip-dump         # skip slow dump analysis\n"
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
        help="hours to look back in event logs (default: 48)",
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
        "--verbose", "-v",
        action="store_true",
        help="show detailed event log entries",
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

    # -- Info --
    info = p.add_argument_group("info")
    info.add_argument(
        "--version", "-V",
        action="version",
        version=f"wtf-restarted {get_display_version()} ({__version__})",
    )

    return p


def main(argv=None):
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "history":
        _cmd_history(args)
    else:
        _cmd_diagnose(args)


def _cmd_diagnose(args):
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

    # Run investigation
    results = run_investigation(
        lookback_hours=args.hours,
        skip_dump=args.skip_dump,
        context_minutes=args.context_minutes,
        verbose=args.verbose,
    )

    if "error" in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        if results.get("stderr"):
            print(f"Details: {results['stderr']}", file=sys.stderr)
        sys.exit(1)

    # Standard output (unless --ai-only)
    if not args.ai_only:
        if args.json_output:
            # JSON with AI: handled below after AI runs
            if not args.ai:
                print(json.dumps(results, indent=2))
                return
        else:
            render.render_diagnosis(results, verbose=args.verbose)

    # AI analysis (if requested)
    if args.ai:
        _run_ai_analysis(args, results, render)


def _run_ai_analysis(args, results, render):
    """Run AI analysis and display or merge results."""
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
        return

    # Show progress indicator
    if not args.ai_verbose and not args.json_output:
        print("\nRunning AI analysis...", file=sys.stderr, flush=True)

    ai_result = analyze(
        results,
        backend_name=backend,
        verbose=args.ai_verbose,
        timeout=120,
    )

    if args.json_output:
        # Merge AI results into the main output
        results["ai_analysis"] = {
            "success": ai_result["success"],
            "backend": backend,
            "sections": ai_result["sections"],
            "error": ai_result["error"],
        }
        print(json.dumps(results, indent=2))
    elif ai_result["success"]:
        render.render_ai_analysis(ai_result["sections"])
    elif backend == "prompt-only":
        # prompt-only returns success=False but isn't an error --
        # the prompt was saved successfully for manual use
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
