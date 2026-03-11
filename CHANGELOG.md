# Changelog

All notable changes to wtf-restarted will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2026-03-11

### Added

- **Restart diagnosis**: Analyzes Windows event logs to determine why the last restart happened, producing a plain-language verdict (BSOD, Unexpected Shutdown, Initiated Restart, Clean Restart, Mixed Signals)
- **Evidence collection**: Checks Kernel-Power Event 41, Event 6008, shutdown initiator (1074/1076), BugCheck/WER events, WHEA hardware errors, Windows Update activity, application crashes, and GPU driver TDR events
- **Crash dump analysis**: Optional Phase 2 analysis via `kd.exe` (!analyze -v) with automatic symbol resolution
- **Restart history**: `history` command shows restart timeline over configurable number of days
- **Surrounding events context**: Shows event log entries from the minutes before a restart for additional diagnostic context
- **RDP session detection**: Warns users connected via Remote Desktop that missing windows may be a session issue rather than a restart
- **Rich terminal output**: Color-coded verdict panels, evidence tables, and event timelines using Rich library
- **JSON output**: `--json` flag for machine-readable output, suitable for piping to other tools or AI analysis
- **Dual entry points**: `wtf-restarted` and `wtfr` CLI commands
- **Modular PowerShell engine**: Investigation logic runs as bundled PS1 scripts with structured JSON output
- **Graceful degradation**: Works without admin privileges (with warnings), without kd.exe (skips dump analysis), and without AI tools (pure local analysis)

### Architecture

- Python CLI (argparse + Rich) orchestrating modular PowerShell scripts
- Based on `crash_investigator.ps1` from the SYSDIAGNOSE project, modularized and enhanced
- Project scaffolding from teeclip template (versioning, git hooks, CI/CD workflows)

[0.1.0-alpha]: https://github.com/djdarcy/wtf-restarted/releases/tag/v0.1.0a1
