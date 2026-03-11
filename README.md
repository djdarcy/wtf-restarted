# wtf-restarted

[![PyPI](https://img.shields.io/pypi/v/wtf-restarted?color=green)](https://pypi.org/project/wtf-restarted/)
[![Release Date](https://img.shields.io/github/release-date/djdarcy/wtf-restarted?color=green)](https://github.com/djdarcy/wtf-restarted/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-green.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![GitHub Discussions](https://img.shields.io/github/discussions/djdarcy/wtf-restarted)](https://github.com/djdarcy/wtf-restarted/discussions)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](docs/platform-support.md)

**Why did my Windows PC restart?** One command, instant answers.

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

| Check | Event IDs | What It Means |
|-------|-----------|---------------|
| Dirty shutdown | 41, 6008 | Power loss, hardware reset, or BSOD |
| Shutdown initiator | 1074, 1076 | Which process asked for the restart |
| BugCheck / BSOD | 1001 (WER) | Blue screen crash details |
| WHEA errors | WHEA-Logger | Hardware faults (CPU, memory, PCIe) |
| Windows Update | 19, 20 | Update installs near restart time |
| App crashes | Application Error | Programs that crashed before reboot |
| GPU driver events | 4101, 4097 | Display driver TDR / recovery |
| Power transitions | 109 | Sleep/wake/hibernate state changes |
| Crash dumps | MEMORY.DMP, Minidump | BSOD dump files for deep analysis |
| Boot sequence | 6005, 6006, 6009 | Clean vs dirty shutdown pattern |
| RDP session | WTS API | Detects Remote Desktop vs console |

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
