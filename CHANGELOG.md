# Changelog

All notable changes to wtf-restarted will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1-alpha] - 2026-03-13

### Added

- **Three-tier progressive disclosure** ([#17](https://github.com/djdarcy/wtf-restarted/issues/17)): Tier 0 (verdict), Tier 1 (evidence), Tier 2 (diagnostics) with interactive keypress paging between tiers
- **`--tier`**: select which tiers to show (`--tier 0` for quick answer, `--tier 1,2` for evidence + diagnostics)
- **`--no-page`**: disable interactive paging between tiers
- **Boot-anchored lookback**: default mode auto-extends past 48h to cover the most recent restart; explicit `--hours` uses a strict time window with informative notes about window behavior
- **AI response caching** ([#18](https://github.com/djdarcy/wtf-restarted/issues/18)): SHA-256 hash with semantic event fingerprint ([#20](https://github.com/djdarcy/wtf-restarted/issues/20)), 24-hour TTL, `--ai-refresh` to bypass cache. Cache key uses event counts + sorted timestamps so `--hours 60` and `--hours 80` hit the same cache when they find identical events
- **THAC0 verbosity system** ([#14](https://github.com/djdarcy/wtf-restarted/issues/14)): ported log_lib, core_lib, and help_lib from github-traffic-tracker -- 14 project-agnostic library files for structured output control
- **Application channel definitions** (`wtf_restarted/output/channels.py`): 13 output channels (verdict, evidence, events, dump, context, system, history, ai, progress, hint, error, trace, general)
- **`-v` stacking**: `-v`/`-vv`/`-vvv` for incremental verbosity (changed from boolean to counter)
- **Evidence severity coloring**: red for bad (dirty shutdown, bugcheck, WHEA), cyan for info (initiator, WU), green for data (crash dump)
- **Demo build script** (`scripts/build_demo.py`): automated VHS recording + gifsicle post-processing pipeline
- **Session log search** (`scripts/search_sesslog.py`): search Claude Code session transcripts for commands, code, and decisions from previous sessions
- **AI parameters documentation** in docs/parameters.md: backends, usage examples, JSON integration, prompt-only workflow
- **Temporal query roadmap** ([#19](https://github.com/djdarcy/wtf-restarted/issues/19)): forward reference in docs for planned `--days`, `--time` range, and targeted investigation features

### Changed

- **investigate.ps1**: all event queries use boot-anchored `$restartLookback` instead of `$lookback`; new `-StrictLookback` switch; dump recency uses date comparison; JSON output includes `lookback_extended`, `lookback_actual_hours`, `strict_lookback`
- **cli.py**: refactored `_run_ai_analysis` into `_get_ai_sections` (returns dict) + `_report_ai_failure`; lazy AI fetcher callback for deferred execution during rendering; THAC0 initialization at startup
- **render.py**: split monolithic `render_diagnosis` into `_render_tier0`, `_render_tier1`, `_render_tier2` with content detection helpers; `render_diagnosis` is now the paging orchestrator; em dash replaced with ASCII `--`
- **VHS demo tape**: updated for three-tier paging with AI analysis scene

### Fixed

- **Verdict regression**: Event 1074 aged out of 48h default window when uptime exceeded 48h, causing "CLEAN RESTART" instead of "INITIATED RESTART" -- boot-anchored lookback ensures verdict-critical events are always found
- **`.gitignore`**: `lib/` pattern matched `wtf_restarted/lib/` -- changed to `/lib/` so only root-level lib/ is excluded (same for `lib64/`)
- **`render_history`**: missing f-prefix on "No restart events" format string
- **`-v` flag tests**: updated for count-based verbose (assertions use `== 1` not `is True`)
- **`_cmd_diagnose` mock**: updated for new `argv` parameter

### Tests

- **116 -> 154** tests (+38: 23 THAC0 library sanity, 14 semantic fingerprint/cache key, 1 verbose stacking)

## [0.2.0-alpha] - 2026-03-12

The 0.2.x series focuses on AI-enhanced diagnosis, with supporting improvements to logging infrastructure and output presentation.

### Added

- **AI-enhanced diagnosis** ([#7](https://github.com/djdarcy/wtf-restarted/issues/7)): opt-in AI analysis via `--ai [BACKEND]` that produces plain-language explanations of restart causes, remediation steps, and calibrated confidence levels
- **AI backends**: Claude Code CLI (`--ai claude`) and prompt-only (`--ai prompt-only`) that saves the prompt to `~/.wtf-restarted/ai/` for manual use with any AI tool
- **`--ai-only`**: suppress standard output and show only the AI analysis
- **`--ai-verbose`**: stream AI response in real-time
- **Rich AI panel**: color-coded confidence (green/yellow/red), structured 4-section format (What Happened / Why / What To Do / Confidence)
- **JSON AI integration**: `--json --ai` merges `ai_analysis` key into output
- **Subprocess smoke tests** (`test_cli_subprocess.py`): 13 tests exercising the real CLI binary via `subprocess.run`, catching argparse and entry-point bugs that in-process tests miss
- **AI unit tests** (`test_ai_analyzer.py`): 13 tests for prompt building, response parsing, backend loading
- **Test infrastructure**: `cli_runner` fixture for integration tests; `ai_output_dir` autouse fixture preventing test artifact leakage (opt out with `@pytest.mark.keep_ai_output`)
- **Investigation scripts** (`tests/one-offs/thinking/`): ttyd ConPTY and VHS capture debugging scripts from the demo GIF sessions ([#5](https://github.com/djdarcy/wtf-restarted/issues/5))

### Changed

- **Verdict engine**: Event 1074 messages now parsed into structured fields (initiator process, user, reason, reason code, shutdown type) -- verdicts say "Windows Update (TrustedInstaller.exe) restarted your PC" instead of generic "A process or user requested the restart"
- **Message truncation**: increased from 300 to 1000 chars for shutdown initiator, 150 to 500 for boot sequence events (preserves full messages for AI analysis)
- **CONTRIBUTING.md**: expanded from stub to full developer guide covering setup, project structure, test architecture, versioning, and contribution areas
- **README.md**: Features section moved above the fold; added link to CONTRIBUTING.md

### Fixed

- Mermaid diagram rendering on GitHub: `\n` replaced with `<br/>` in node labels (platform-support.md, powershell-engine.md)

### Tests

- **66 -> 116** tests (+50 new across 3 test files)

## [0.1.1] - 2026-03-12

### Added

- **VHS demo GIF** in README replacing ASCII art sample output ([#5](https://github.com/djdarcy/wtf-restarted/issues/5))
- **Demo render script** (`scripts/demo_render.py`): standalone mock-data renderer for CI/dev use without Windows event logs
- **VHS tape files** (`scripts/vhs/`): demo and test recording scripts for terminal GIF generation
- **Documentation suite**: Platform support, PowerShell engine architecture, parameters reference, and Windows event ID reference docs
- **Mermaid diagrams**: Architecture flowcharts in powershell-engine.md and platform-support.md
- **VS Code debug configs**: Launch configurations for diagnose, history, and pytest
- **GitHub issue tracker**: Epics for AI diagnosis (#7), commercial MCP service (#8); issues for mcp-windbg (#9), auto-install kd.exe (#10), port exhaustion (#11)
- **GitHub traffic tracking** via ghtraf (badge gist, archive gist, stats dashboard)

### Changed

- **License**: GPL v3 to AGPL v3 with dual licensing (commercial license available)
- **README**: Demo GIF with static JPG fallback; rewritten "What It Checks" as narrative prose with Microsoft docs links; streamlined roadmap with link to ROADMAP.md and [#3](https://github.com/djdarcy/wtf-restarted/issues/3)
- **Platform badge**: Links to platform-support.md; reflects Windows-only current state
- **CI**: Simplified test matrix to Windows-only (matching platform support)

### Fixed

- CI matrix: remove Python 3.9 (requires-python >= 3.10)
- Git hooks: replaced teeclip references with wtf-restarted in pre-push, install-hooks, and update-version scripts
- Version tests: decoupled from hardcoded phase values so they work across version bumps
- Version string: `__version__` now updated by git hooks with correct commit hash

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

[0.2.1-alpha]: https://github.com/djdarcy/wtf-restarted/compare/v0.2.0a1...v0.2.1a1
[0.2.0-alpha]: https://github.com/djdarcy/wtf-restarted/compare/v0.1.1...v0.2.0a1
[0.1.1]: https://github.com/djdarcy/wtf-restarted/releases/tag/v0.1.1
[0.1.0-alpha]: https://github.com/djdarcy/wtf-restarted/releases/tag/v0.1.0a1
