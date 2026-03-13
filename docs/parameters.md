# Parameters Reference

wtf-restarted can be invoked in two ways: through the **Python CLI** (`wtf-restarted` / `wtfr`) or by running the **PowerShell scripts** directly. Both interfaces expose similar controls but with different syntax.

## Python CLI

### Commands

The CLI has two commands. If omitted, `diagnose` is the default.

```bash
wtf-restarted                # same as: wtf-restarted diagnose
wtf-restarted diagnose       # analyze the most recent restart
wtf-restarted history        # show restart timeline
```

Both `wtf-restarted` and `wtfr` are registered as entry points -- they're identical.

### Diagnosis Parameters

These apply to the `diagnose` command (the default).

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--hours N` | `-H N` | int | 48 | How far back to search event logs. When omitted, auto-extends to cover the last restart. When explicit, uses a strict time window. |
| `--skip-dump` | | flag | off | Skip crash dump analysis. Useful when you want a quick answer and don't need BSOD details, or when `kd.exe` is slow to download symbols. |
| `--context-minutes N` | | int | 10 | How many minutes of surrounding events to show before the restart. Increase to see more of what was happening leading up to the event. |

#### How `--hours` works

**Default behavior (no `--hours` flag):** The tool automatically extends the lookback window to cover the most recent restart, even if it happened more than 48 hours ago. This ensures you always get a verdict. If the window was extended, a note tells you:

```
Note: No restart events in last 48h -- looked back 72h to cover last restart.
      Use --hours 48 for strict 48h window.
```

**Explicit `--hours N`:** Uses a strict N-hour window. If the restart falls outside it, the tool reports what it found (which may be nothing) and suggests a wider window:

```
Note: Last restart was ~72h ago, outside your --hours 24 window.
      Run without --hours or use --hours 73 to include it.
```

This is useful for monitoring scripts, scheduled health checks, or when you specifically want to know "did anything happen in the last N hours?"

#### When to adjust `--hours`

Most users never need to -- the default auto-extends to find the restart. Use explicit `--hours` when:
- You want a strict time-slice: "what happened in the last 8 hours?" (`--hours 8`)
- Scripting or CI/CD: a strict window avoids false positives from old restarts
- Investigating a pattern over the past week (`--hours 168`)

Note that larger windows mean more event log entries to scan, so queries take slightly longer.

Future enhancements (`--days`, `--time` date ranges, targeted investigation) are tracked in [Issue #19](https://github.com/djdarcy/wtf-restarted/issues/19).

#### When to use `--skip-dump`

Crash dump analysis (`kd.exe`) is the slowest part of the investigation -- it can take 30-60 seconds while downloading debug symbols from Microsoft's servers. Use `--skip-dump` when:
- You just want the verdict quickly
- You know it wasn't a BSOD (e.g., you saw Windows Update restarting)
- `kd.exe` isn't installed (the tool will note this, but `--skip-dump` avoids the check entirely)
- You're running in a script and want fast turnaround

#### When to adjust `--context-minutes`

The context window shows Warning/Error/Critical events from the System and Application logs in the minutes before a restart. This helps answer "what was happening right before the machine went down?"

- Default 10 minutes is usually enough for sudden crashes
- Increase to 30+ if investigating a slow degradation (e.g., mounting errors before a crash)
- Set to 0 to skip the context window entirely

### History Parameters

These apply to the `history` command.

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--days N` | `-d N` | int | 30 | How many days of restart history to show. |

```bash
wtf-restarted history              # last 30 days
wtf-restarted history --days 90    # last 3 months
wtf-restarted history --days 365   # full year (if logs go back that far)
```

Event logs have a maximum retention size. On most systems, the System log keeps 30-90 days of events depending on volume and the configured maximum log size. Requesting `--days 365` won't fail -- it just returns whatever is available.

### Output Parameters

These work with both `diagnose` and `history`.

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--json` | | flag | off | Output raw JSON instead of Rich-formatted tables. |
| `--verbose` | `-v` | flag | off | Show all event log entries, not just the summary. |

#### JSON mode

JSON output writes to stdout with no color codes or formatting -- suitable for piping, saving to files, or feeding to other tools:

```bash
# Save a report
wtf-restarted --json > restart-report.json

# Extract just the verdict
wtf-restarted --json | jq .verdict.type

# Feed to AI for analysis
wtf-restarted --json | claude "explain this restart report"

# Use in a script
$data = wtf-restarted --json | python -c "import sys,json; d=json.load(sys.stdin); print(d['verdict']['type'])"
```

The JSON schema is documented in [powershell-engine.md](powershell-engine.md#json-output-schema).

#### Verbose mode

Verbose mode shows raw event log entries for every category, even when no relevant events were found. Without it, the output only shows categories where evidence was found. Useful for:
- Confirming the tool checked everything (not just what it reported)
- Seeing low-priority events that didn't affect the verdict
- Debugging the tool's behavior

### AI Analysis Parameters

These apply to the `diagnose` command and enable opt-in AI-powered analysis.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--ai [BACKEND]` | optional string | claude | Enable AI analysis after standard output. Backend choices: `claude`, `codex`, `prompt-only`. |
| `--ai-only [BACKEND]` | optional string | claude | Show only AI analysis, suppress standard diagnostic output. |
| `--ai-verbose` | flag | off | Stream AI response in real-time instead of waiting for completion. |

```bash
# AI analysis with Claude Code CLI (default backend)
wtf-restarted --ai

# AI analysis with a specific backend
wtf-restarted --ai codex

# Save prompt to file for manual use with any AI tool
wtf-restarted --ai prompt-only

# Only show the AI analysis, skip the standard tables/verdict
wtf-restarted --ai-only

# Combine with JSON output
wtf-restarted --json --ai
```

#### Backends

| Backend | Requires | What it does |
|---------|----------|-------------|
| `claude` (default) | [Claude Code CLI](https://claude.ai/claude-code) installed | Invokes Claude via subprocess, returns structured analysis |
| `codex` | Codex CLI installed | *(planned -- not yet implemented)* |
| `prompt-only` | Nothing | Saves the full diagnostic prompt to `~/.wtf-restarted/ai/` as a timestamped `.md` file. Paste it into any AI tool manually. |

#### How `--ai` works

1. Standard investigation runs normally (event logs, crash dumps, verdict)
2. Results are serialized to JSON and embedded in a diagnostic prompt template
3. The prompt is sent to the selected backend (or saved to file for `prompt-only`)
4. The AI response is parsed into four sections: **What Happened**, **Why**, **What To Do**, **Confidence**
5. Results display in a Rich panel with color-coded confidence (green = high, yellow = medium, red = low)

If the backend is unavailable (e.g., Claude Code CLI not installed), the tool prints a message and continues with standard output only. The `prompt-only` backend is always available and works as a free-tier option.

#### `--ai-only` vs `--ai`

- `--ai`: shows standard diagnostic output first, then appends AI analysis
- `--ai-only`: suppresses standard output entirely -- only the AI panel is shown
- `--ai-only` implies `--ai` with the same backend

#### JSON + AI

When `--json` and `--ai` are combined, the JSON output includes an `ai_analysis` key:

```json
{
  "system": { ... },
  "evidence": { ... },
  "verdict": { ... },
  "ai_analysis": {
    "success": true,
    "backend": "claude",
    "sections": {
      "what_happened": "...",
      "why": "...",
      "what_to_do": "...",
      "confidence": "..."
    },
    "error": null
  }
}
```

#### Prompt files

The `prompt-only` backend saves prompts to `~/.wtf-restarted/ai/` with timestamped filenames:

```
~/.wtf-restarted/ai/
  prompt_2026-03-12_18-30-45.md
  prompt_2026-03-12_19-15-22.md
```

These files contain the complete diagnostic context and can be pasted into ChatGPT, Claude, or any AI assistant. The output includes a link to a [recommended GPT](https://chatgpt.com/g/g-Pn1omABcF-devop-it-scripting-guru) configured for IT diagnostics.

### Info

| Flag | Short | Description |
|------|-------|-------------|
| `--version` | `-V` | Print version string and exit. |

---

## PowerShell Scripts

The PowerShell scripts can be run without Python installed. They live in `wtf_restarted/ps1/` in the package (or repo).

### investigate.ps1

Full restart/crash investigation. This is the engine behind `wtf-restarted diagnose`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-LookbackHours` | int | 48 | Hours to search back in event logs |
| `-ContextMinutes` | int | 10 | Minutes of surrounding events before restart |
| `-SkipDump` | switch | off | Skip crash dump analysis |
| `-JsonOnly` | switch | off | Output only compact JSON (no human-readable text) |
| `-DumpFile` | string | auto-detect | Path to a specific crash dump file to analyze |
| `-SymbolPath` | string | MS symbol server | Symbol path for `kd.exe` |

```powershell
# Basic usage -- human-readable report
powershell -File investigate.ps1

# JSON only (what the Python CLI consumes)
powershell -File investigate.ps1 -JsonOnly

# Look back a week, skip dump analysis
powershell -File investigate.ps1 -LookbackHours 168 -SkipDump

# Analyze a specific minidump
powershell -File investigate.ps1 -DumpFile "C:\Windows\Minidump\091124-12345-01.dmp"

# Use a custom symbol path (e.g., local symbol cache)
powershell -File investigate.ps1 -SymbolPath "srv*D:\Symbols*https://msdl.microsoft.com/download/symbols"
```

#### `-DumpFile` -- targeting a specific crash dump

By default, `investigate.ps1` auto-detects crash dumps:
1. Checks `C:\Windows\MEMORY.DMP` for a full memory dump
2. Scans `C:\Windows\Minidump\` for minidump files
3. Picks the most recent dump within the lookback window

Use `-DumpFile` to override this and point at a specific file. Useful when:
- You have multiple minidumps and want to analyze a particular one
- The dump file has been moved to a different location
- You're analyzing dumps from another machine

#### `-SymbolPath` -- debug symbol resolution

When `kd.exe` analyzes a crash dump, it needs debug symbols to decode the bugcheck. The default path downloads symbols from Microsoft's public server to `C:\Symbols`:

```
srv*C:\Symbols*https://msdl.microsoft.com/download/symbols
```

The script checks the `_NT_SYMBOL_PATH` environment variable first. If set, that takes precedence over the default. The `-SymbolPath` parameter overrides both.

If you already have symbols downloaded or use a corporate symbol server, point this there to avoid re-downloading:

```powershell
# Use existing WinDbg symbol cache
powershell -File investigate.ps1 -SymbolPath "srv*C:\Users\me\AppData\Local\Temp\SymbolCache*https://msdl.microsoft.com/download/symbols"
```

#### Output modes

**Without `-JsonOnly`**: prints a formatted report to the console (via `Write-Host`) followed by a `--- JSON OUTPUT ---` section. The JSON is written to stdout (`Write-Output`), so you can capture it while still seeing the report:

```powershell
# See the report AND capture JSON
$json = powershell -File investigate.ps1 | Select-String -Pattern '^\{' | Select-Object -Last 1
```

**With `-JsonOnly`**: writes only compact JSON to stdout. No `Write-Host` output. This is the mode the Python CLI uses.

### history.ps1

Restart history timeline. This is the engine behind `wtf-restarted history`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-Days` | int | 30 | How many days of history to return |

```powershell
# Last 30 days (default)
powershell -File history.ps1

# Last 90 days
powershell -File history.ps1 -Days 90

# Parse in PowerShell
$history = powershell -File history.ps1 | ConvertFrom-Json
$history | Where-Object { $_.type -eq "DIRTY_SHUTDOWN" }
```

Output is always compact JSON -- an array of event objects sorted newest-first:

```json
[
  {"time": "2026-03-11 04:42:10", "type": "START", "event_id": 6005, "message": "..."},
  {"time": "2026-03-10 23:15:02", "type": "INITIATED_RESTART", "event_id": 1074, "message": "..."},
  {"time": "2026-03-10 23:14:58", "type": "CLEAN_STOP", "event_id": 6006, "message": "..."}
]
```

Event types: `START`, `CLEAN_STOP`, `DIRTY_SHUTDOWN`, `INITIATED_RESTART`, `BSOD`.

---

## Parameter Mapping

How the Python CLI flags map to the underlying PowerShell parameters:

| Python CLI | PowerShell (investigate.ps1) | PowerShell (history.ps1) |
|-----------|------------------------------|--------------------------|
| `--hours N` | `-LookbackHours N -StrictLookback` | -- |
| *(default, no --hours)* | `-LookbackHours 48` *(boot-anchored)* | -- |
| `--skip-dump` | `-SkipDump` | -- |
| `--context-minutes N` | `-ContextMinutes N` | -- |
| `--days N` | -- | `-Days N` |
| `--json` | `-JsonOnly` | *(always JSON)* |
| `--verbose` | *(Python-side only)* | -- |
| `--ai [BACKEND]` | *(Python-side only)* | -- |
| `--ai-only [BACKEND]` | *(Python-side only)* | -- |
| `--ai-verbose` | *(Python-side only)* | -- |
| -- | `-DumpFile "path"` | -- |
| -- | `-SymbolPath "path"` | -- |

Note that `-DumpFile` and `-SymbolPath` are only available through the PowerShell script directly. The Python CLI does not expose these yet -- if you need that level of control, use the PS1 scripts.

`--verbose` is handled on the Python side -- it controls whether the Rich renderer shows all event categories or only those with findings. The PowerShell script always collects everything regardless.

---

## Elevation / Admin Privileges

Both the Python CLI and the PowerShell scripts work without Administrator privileges, but some data sources require elevation:

| Data Source | Needs Admin? | What You Miss Without It |
|-------------|-------------|--------------------------|
| System event log (most events) | No | Nothing -- readable by all users |
| Security event log | Yes | Login/logoff events (not currently checked) |
| `C:\Windows\MEMORY.DMP` | Yes | Full crash dump analysis |
| `C:\Windows\Minidump\` | Usually no | Varies by system policy |
| `kd.exe` dump analysis | Yes | Bugcheck code, faulting module, failure bucket |

The Python CLI prints a warning to stderr when not elevated. The PowerShell scripts run silently -- errors from inaccessible logs are suppressed with `-ErrorAction SilentlyContinue`.

For the most complete results, run from an elevated terminal:

```powershell
# Right-click Terminal -> Run as Administrator, then:
wtf-restarted

# Or from an elevated PowerShell:
powershell -File investigate.ps1
```
