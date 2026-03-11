# wtf-restarted

[![PyPI](https://img.shields.io/pypi/v/wtf-restarted?color=green)](https://pypi.org/project/wtf-restarted/)
[![Release Date](https://img.shields.io/github/release-date/djdarcy/wtf-restarted?color=green)](https://github.com/djdarcy/wtf-restarted/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-green.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![Installs](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/djdarcy/c350f8487c9510480a341f4d3274de0a/raw/installs.json)](https://djdarcy.github.io/wtf-restarted/stats/#installs)
[![GitHub Discussions](https://img.shields.io/github/discussions/djdarcy/wtf-restarted)](https://github.com/djdarcy/wtf-restarted/discussions)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](docs/platform-support.md)

**WhyTF did my Windows PC restart?** One command, instant answers.

## The Problem

Your Windows PC restarted and you don't know why. Maybe you were away. Maybe it happened overnight. You come back to a fresh desktop and zero context. The "official" answer is to open Event Viewer, navigate through layers of cryptic logs, and decode event IDs. Most users never do this.

**wtf-restarted** reads the same event logs, crash dumps, and system state that Event Viewer uses -- but gives you a plain-language verdict instead of raw event XML.

## Quick Start

```bash
pip install wtf-restarted
wtf-restarted
```

That's it. You'll see something like:

```
+----------------------------------------------+
| WTF-RESTARTED -- Last Restart Analysis       |
+----------------------------------------------+
  Last boot:       2026-03-11 04:42:10
  Current uptime:  0.11:38:43
  Computer:        PLZWORK

+------------------- VERDICT ------------------+
| INITIATED RESTART                            |
|                                              |
| Windows Update triggered the restart.        |
|   - KB5079473 (Security Update) installed    |
|   - TrustedInstaller.exe initiated reboot    |
+----------------------------------------------+
```

## What It Checks

The tool reads the same Windows Event Logs that Event Viewer uses, but focuses on the events that actually matter for answering "why did my PC restart?"

It starts by looking for signs of a **dirty shutdown** -- the kernel-level markers (Event 41, 6008) that Windows records when the system didn't shut down cleanly. This catches power losses, hard resets, and BSODs.

Next, it checks whether a **process requested the restart** (Event 1074). This is how Windows tracks which program -- usually Windows Update, but sometimes a user or an installer -- asked the system to reboot. If a restart was requested *and* the shutdown was clean, the answer is straightforward.

For crashes, the tool looks for **BugCheck reports** from Windows Error Reporting, **crash dump files** on disk (`MEMORY.DMP`, minidumps), and **WHEA hardware errors** that point to CPU, memory, or PCIe faults. If `kd.exe` (the Windows SDK debugger) is installed, it can crack open the dump file and extract the exact bugcheck code and faulting driver.

It also collects supporting context: **Windows Update activity** near the restart time, **application crashes** in the hour before reboot, **GPU driver timeouts** (TDR events), **power state transitions** (sleep/wake/hibernate), and the **boot/shutdown sequence** to distinguish clean restarts from dirty ones. If you're connected via **Remote Desktop**, it warns you that your "missing windows" might just be on a different session.

For the full list of event IDs, providers, manual lookup steps, and how to add your own checks, see [docs/event-reference.md](docs/event-reference.md).

## Commands

```bash
# Why did my PC restart? (default command)
wtf-restarted

# Short alias
wtfr

# Show restart history (last 30 days)
wtf-restarted history
wtf-restarted history --days 90

# Look further back
wtf-restarted --hours 72

# Skip crash dump analysis (faster)
wtf-restarted --skip-dump

# Show more surrounding events for context
wtf-restarted --context-minutes 30

# Machine-readable JSON output
wtf-restarted --json

# Verbose mode (all event categories)
wtf-restarted -v
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

## Features

- **Plain-language verdicts**: No event IDs to decode -- just "Windows Update restarted your PC" or "BSOD caused by nvlddmkm.sys"
- **Restart history**: See patterns over time (is your PC crashing every week?)
- **Surrounding events**: Shows what happened in the minutes before a restart for context
- **RDP awareness**: Warns if you're in a Remote Desktop session and your "missing windows" might just be on a different session
- **Crash dump analysis**: If `kd.exe` (Windows SDK Debugger) is installed, extracts bugcheck code, faulting module, and failure bucket from crash dumps
- **JSON output**: Pipe to `jq`, save to file, or feed to AI tools for deeper analysis
- **Zero mandatory dependencies**: Core analysis uses only PowerShell (built into Windows). The Python CLI adds Rich for pretty output.

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

## Installation

```bash
# From PyPI
pip install wtf-restarted

# From source
git clone https://github.com/djdarcy/wtf-restarted.git
cd wtf-restarted
pip install -e ".[dev]"
```

## Roadmap

- [ ] VHS terminal demo GIF ([charmbracelet/vhs](https://github.com/charmbracelet/vhs))
- [ ] AI-enhanced diagnosis (Claude Code, Codex integration)
- [ ] Auto-install helper for kd.exe / Windows SDK
- [ ] mcp-windbg integration for structured dump analysis
- [ ] Cross-platform support (Linux via journalctl/dmesg, macOS via log show)
- [ ] Port exhaustion detection
- [ ] Integration with [Stop-Windows-Restarting](https://github.com/djdarcy/Stop-Windows-Restarting)
- [ ] Export to HTML report
- [ ] Standalone .exe distribution (PyInstaller)

## Related Projects

- **[Stop-Windows-Restarting](https://github.com/djdarcy/Stop-Windows-Restarting)** -- Prevent Windows Update from forcing reboots (complementary: diagnose vs prevent)
- **[mcp-windbg](https://github.com/svnscha/mcp-windbg)** -- MCP server for WinDbg (future integration target)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

Like the project?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/djdarcy)

## License

wtf-restarted, Copyright (C) 2026 Dustin Darcy

This project is licensed under the GNU General Public License v3.0 -- see [LICENSE](LICENSE) for details.
