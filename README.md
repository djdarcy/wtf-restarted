# wtf-restarted

[![PyPI](https://img.shields.io/pypi/v/wtf-restarted?color=green)](https://pypi.org/project/wtf-restarted/)
[![Release Date](https://img.shields.io/github/release-date/djdarcy/wtf-restarted?color=green)](https://github.com/djdarcy/wtf-restarted/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-green.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Installs](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/djdarcy/c350f8487c9510480a341f4d3274de0a/raw/installs.json)](https://djdarcy.github.io/wtf-restarted/stats/#installs)
[![GitHub Discussions](https://img.shields.io/github/discussions/djdarcy/wtf-restarted)](https://github.com/djdarcy/wtf-restarted/discussions)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](docs/platform-support.md)

**WhyTF did my Windows PC restart?** One command, instant answers.

## The Problem

Your Windows PC restarted and you don't know why. Maybe you were away. Maybe it happened overnight. You come back to a fresh desktop and zero context. The "official" answer is to open Event Viewer, navigate through layers of cryptic logs, and decode event IDs. Most users never do this.

**wtf-restarted** reads the same event logs, crash dumps, and system state that Event Viewer uses, but gives you a plain-language verdict instead of raw event XML.

## Quick Start

```bash
pip install wtf-restarted
wtf-restarted
```

That's it. You'll see something like:

<p align="center">
  <picture>
    <img src="docs/images/demo-lossy80.gif" alt="wtf-restarted demo showing verdict and evidence summary">
  </picture>
  <br>
  <sub><a href="docs/images/demo.jpg">Static screenshot</a> if the GIF doesn't load</sub>
</p>

## Features

- **Plain-language verdicts**: No event IDs to decode -- just "Windows Update restarted your PC" or "BSOD caused by nvlddmkm.sys"
- **Restart history**: See patterns over time (is your PC crashing every week?)
- **Surrounding events**: Shows what happened in the minutes before a restart for context
- **RDP awareness**: Warns if you're in a Remote Desktop session and your "missing windows" might just be on a different session
- **Crash dump analysis**: If `kd.exe` (Windows SDK Debugger) is installed, extracts bugcheck code, faulting module, and failure bucket from crash dumps
- **AI-ready diagnostics**: `--ai prompt-only` saves a diagnostic prompt to file -- paste it into ChatGPT, Claude, or any AI tool for a plain-language explanation (no API key required). Or use `--ai` with Claude Code CLI for inline analysis.
- **JSON output**: Pipe to `jq`, save to file, or feed to AI tools for deeper analysis
- **Zero mandatory dependencies**: Core analysis uses only PowerShell (built into Windows). The Python CLI adds Rich for pretty output.

## What It Checks

**WTF-restarted** (pronounced: *wut-thuh-eff re-tar-ded*) reads the same Windows Event Logs that Event Viewer uses, but focuses on the events that actually matter for answering "why did my PC restart?"

It starts by looking for signs of a **dirty shutdown**. For example,  Windows records kernel-level markers like [Event 41](https://learn.microsoft.com/en-us/windows/client-management/troubleshoot-event-id-41-restart) and [6008](docs/event-reference.md#event-6008----previous-shutdown-was-unexpected), which are indicators the system didn't shut down cleanly. This catches power losses, hard resets, and BSODs.

Next, `wtfr` checks whether a **process requested the restart** ([Event 1074](docs/event-reference.md#event-1074----process-initiated-restartshutdown)). This is how Windows tracks which program (usually Windows Update, but sometimes a user or an installer) asked the system to reboot. If a restart was requested *and* the shutdown was clean, the answer is straightforward.

For crashes, the tool looks for **BugCheck reports** from Windows Error Reporting, **crash dump files** on disk (`MEMORY.DMP`, minidumps), and **[WHEA hardware errors](https://learn.microsoft.com/en-us/windows-hardware/drivers/whea/)** that point to CPU, memory, or PCIe faults. If `kd.exe` (the Windows SDK debugger) is installed, it can crack open the dump file and extract the exact bugcheck code and faulting driver.

It also collects supporting context: **Windows Update activity** near the restart time, **application crashes** in the hour before reboot, **[GPU driver timeouts](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery)** (TDR events), **power state transitions** (sleep/wake/hibernate), and the **boot/shutdown sequence** to distinguish clean restarts from dirty ones. If you're connected via **Remote Desktop**, it warns you that your "missing windows" might just be on a different session.

For the full list of event IDs, providers, manual lookup steps, and how to add your own checks, see [docs/event-reference.md](docs/event-reference.md).

## Commands

```bash
# Why did my PC restart? (default command)
wtf-restarted   #Or the short alias: wtfr

# Show restart history (last 30 days)
wtf-restarted history
wtf-restarted history --days 90

# Look further back
wtf-restarted --hours 72

# Skip crash dump analysis (faster)
wtf-restarted --skip-dump

# Show more surrounding events for context
wtf-restarted --context-minutes 30

# AI analysis -- saves prompt for any AI tool (no API key needed)
wtf-restarted --ai prompt-only

# AI analysis with Claude Code CLI (if installed)
wtf-restarted --ai

# Machine-readable JSON output
wtf-restarted --json

# Verbose mode (all event categories)
wtf-restarted -v

# Quiet mode (reduced output)
wtf-restarted -Q          # reduced detail
wtf-restarted -QQ         # header + verdict only

# Per-channel verbosity control
wtf-restarted --show events:-4    # suppress events, keep everything else
```

For detailed parameter descriptions, defaults, and guidance on when to adjust each flag, see [docs/parameters.md](docs/parameters.md).

## Verdict Types

| Verdict | Color | Meaning |
|---------|-------|---------|
| **BSOD** | Red | Blue Screen of Death -- crash dump found |
| **UNEXPECTED SHUTDOWN** | Yellow | Dirty shutdown, no initiator (power loss, hardware reset) |
| **INITIATED RESTART** | Cyan | A process requested the restart (often Windows Update) |
| **MIXED SIGNALS** | Magenta | Both dirty shutdown and restart initiator found |
| **CLEAN RESTART** | Green | Normal, expected restart |

## Using the PowerShell Scripts Directly

The investigation engine is a standalone PowerShell script that works without Python. If you prefer PowerShell or want to integrate restart diagnosis into your own scripts:

```powershell
# Run the investigation directly
powershell -File investigate.ps1

# Get JSON output for scripting
powershell -File investigate.ps1 -JsonOnly | ConvertFrom-Json

# Look back further, skip dump analysis
powershell -File investigate.ps1 -LookbackHours 72 -SkipDump
```

See [docs/powershell-engine.md](docs/powershell-engine.md) for the full parameter reference, JSON schema, dot-sourcing for interactive use, and integration examples.

## Requirements

- **Windows 10 or 11** (PowerShell 5.1+)
- **Python 3.10+**
- **Administrator** recommended (some event logs require elevation)
- **kd.exe** optional (for crash dump analysis -- part of [Windows SDK Debugging Tools](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/))
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** optional (for AI-enhanced diagnosis via `--ai claude`)
- **[OpenAI Codex CLI](https://github.com/openai/codex)** optional (for AI-enhanced diagnosis via `--ai codex`)

## Installation

```bash
# From PyPI
pip install wtf-restarted

# From source (development)
git clone https://github.com/djdarcy/wtf-restarted.git
cd wtf-restarted
pip install -e ".[dev]"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development setup including virtual environment, test running, and project structure.

## Roadmap

- [x] AI-enhanced diagnosis (`--ai prompt-only`, `--ai` with Claude Code)
- [ ] Auto-install helper for kd.exe / Windows SDK
- [ ] Cross-platform support (Linux, macOS)
- [ ] mcp-windbg integration for structured dump analysis

See [ROADMAP.md](ROADMAP.md) for the full phased plan, or track progress on [issue #3](https://github.com/djdarcy/wtf-restarted/issues/3).

## Related Projects

- **[Stop-Windows-Restarting](https://github.com/djdarcy/Stop-Windows-Restarting)** -- Prevent Windows Update from forcing reboots (complementary: diagnose vs prevent)
- **[mcp-windbg](https://github.com/svnscha/mcp-windbg)** -- MCP server for WinDbg (future integration target)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

Like the project?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/djdarcy)

## License

wtf-restarted, Copyright (C) 2026 Dustin Darcy

This project is dual-licensed:

- **Open source**: [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0) -- see [LICENSE](LICENSE)
- **Commercial**: Contact [djdarcy](https://github.com/djdarcy) for commercial licensing if AGPL terms don't fit your use case

The AGPL is identical to GPL v3, with one addition: if you run a modified version of this software as a network service, you must make your source code available to users of that service. This ensures improvements to the diagnostic engine benefit everyone. Individual and self-hosted use is unaffected.
