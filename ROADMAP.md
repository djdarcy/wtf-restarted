# Roadmap

Tracking issue: [#3](https://github.com/djdarcy/wtf-restarted/issues/3)

## Phase 1: Foundation (current)

- [x] Core restart diagnosis (event logs, crash dumps, verdict engine)
- [x] Rich terminal output with color-coded verdicts
- [x] JSON output mode
- [x] Restart history timeline
- [x] RDP session detection
- [x] Modular PowerShell engine (standalone `.ps1` scripts)
- [x] Shared `ps_runner.py` for subprocess management
- [x] Registry-first kd.exe discovery
- [x] `_NT_SYMBOL_PATH` auto-detection
- [x] CI/CD pipeline (GitHub Actions, 3 OS x 4 Python versions)
- [x] GitHub traffic tracking (ghtraf)
- [ ] VHS terminal demo GIF for README ([#5](https://github.com/djdarcy/wtf-restarted/issues/5))
- [ ] PyPI publication (v0.1.0a1)
- [ ] Enable GitHub Pages for stats dashboard

## Phase 2: Intelligence

- [ ] AI-enhanced diagnosis (Claude Code, Codex backends)
- [ ] mcp-windbg integration for structured dump analysis
- [ ] Auto-install helper for kd.exe / Windows SDK
- [ ] Driver watchlist (user-configurable suspicious driver list)
- [ ] WHEA error code decoder (hex -> plain language)

## Phase 3: Cross-Platform

- [ ] Platform abstraction layer (`PlatformInvestigator` base class)
- [ ] Linux backend: `journalctl`, `/proc/uptime`, `dmesg`, `/var/crash/`
- [ ] macOS backend: `log show`, `sysctl kern.boottime`, DiagnosticReports
- [ ] BSD support (community-driven)
- [ ] See [docs/platform-support.md](docs/platform-support.md) for the full design
- [ ] Tracking issue: [#6](https://github.com/djdarcy/wtf-restarted/issues/6)

## Phase 4: Ecosystem

- [ ] Integration with [Stop-Windows-Restarting](https://github.com/djdarcy/Stop-Windows-Restarting)
- [ ] Port exhaustion detection
- [ ] Scheduled task mode (`wtf-restarted install-task`)
- [ ] Export to HTML report
- [ ] Standalone .exe distribution (PyInstaller)
- [ ] Transfer to [DazzleTools](https://github.com/DazzleTools) org

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| PowerShell as `.ps1` files, not inline Python strings | IDE syntax highlighting, linting, independent testability |
| Registry-first kd.exe discovery (no vcvars) | kd.exe is standalone; vcvars is for MSVC compiler toolchain |
| Tiered dependencies | Basic (PS only) -> Standard (+ kd.exe) -> Advanced (+ mcp-windbg) -> AI-Enhanced |
| `ps_runner.py` shared caller | DRY subprocess management; `run_ps1()` for scripts, `run_ps_command()` for one-liners |

## Ideas Backlog

See [#4 Notes & Quick Ideas](https://github.com/djdarcy/wtf-restarted/issues/4) for the running scratchpad.
