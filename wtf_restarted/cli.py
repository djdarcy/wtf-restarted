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
            "  wtf-restarted                    # diagnose last restart\n"
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

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        render.render_diagnosis(results, verbose=args.verbose)


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
