# Contributing to wtf-restarted

Thank you for considering contributing to wtf-restarted!

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct.
By participating in this project you agree to abide by its terms.

## Development Setup

### Prerequisites

- **Windows 10 or 11** -- the investigation engine reads Windows Event Logs and analyzes crash dumps, so you need a Windows machine to test against real data
- **PowerShell 5.1+** (built into Windows 10/11)
- **Python 3.10+**
- **Git**
- **Administrator privileges** recommended -- some event log categories require elevation to read

### Clone and Install

```bash
git clone https://github.com/djdarcy/wtf-restarted.git
cd wtf-restarted
python -m venv .venv
.venv\Scripts\activate     # Windows cmd
# or: source .venv/Scripts/activate   # Git Bash / WSL
pip install -e ".[dev]"
```

The `-e` flag installs in editable mode so code changes take effect immediately without reinstalling.

### What `[dev]` Installs

The `[dev]` extra (defined in `pyproject.toml`) adds:

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Code coverage reporting |

The core runtime dependency is just `rich` (for terminal formatting). Everything else is either built-in Python or PowerShell.

### Optional: kd.exe for Crash Dump Analysis

If you want to test crash dump analysis features, install the Windows SDK Debugging Tools:

1. Download [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
2. During installation, select only **"Debugging Tools for Windows"**
3. Verify: `where kd.exe` should return a path

Or via command line: `winsdksetup.exe /features OptionId.WindowsDesktopDebuggers /quiet`

## Project Structure

```
wtf-restarted/
|-- wtf_restarted/           # Python package
|   |-- cli.py               # CLI entry point (argparse, Rich output)
|   |-- _version.py          # Version info (auto-updated by git hooks)
|   |-- engine/              # Core logic
|   |   |-- investigator.py  # Orchestrates the investigation
|   |   |-- ps_runner.py     # Runs PowerShell scripts from Python
|   |   |-- history.py       # Restart history tracking
|   |-- output/
|   |   |-- render.py        # Rich terminal rendering (verdicts, tables)
|   |-- ai/                  # AI-enhanced analysis (in progress)
|   |   |-- analyzer.py      # AI backend orchestration
|   |   |-- backends/        # Claude, Codex, prompt-only backends
|   |-- ps1/                 # PowerShell scripts (packaged with pip install)
|       |-- investigate.ps1  # Main investigation engine
|       |-- history.ps1      # Restart history queries
|
|-- tests/                   # pytest test suite
|   |-- conftest.py          # Shared fixtures
|   |-- test_*.py            # Test modules
|   |-- one-offs/            # Exploratory scripts, one-time diagnostics
|   |   |-- thinking/        # Scratch work / analysis scripts
|
|-- scripts/                 # Development utilities
|-- docs/                    # User-facing documentation
```

### How It Works

The architecture is a **Python CLI wrapping a PowerShell engine**:

1. `cli.py` parses arguments and calls `investigator.py`
2. `investigator.py` uses `ps_runner.py` to execute `investigate.ps1` as a subprocess
3. `investigate.ps1` queries Windows Event Logs, checks crash dumps, and returns structured JSON
4. `render.py` formats the JSON into Rich terminal output (verdicts, evidence tables, context)

The PowerShell script is the "real" investigation engine -- it can also run standalone without Python (see `docs/powershell-engine.md`). The Python layer adds the CLI interface, pretty output, and future AI analysis.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=wtf_restarted

# Run a specific test file
pytest tests/test_cli.py

# Run a specific test
pytest tests/test_cli.py::test_version_flag -v
```

### Test Categories

- **Unit tests** (`test_cli.py`, `test_render.py`, `test_version.py`): Test Python logic in isolation, mock PowerShell output
- **Integration tests** (`test_investigator.py`, `test_ps_runner.py`): Actually invoke PowerShell -- require a Windows machine
- **Subprocess tests** (`test_cli_subprocess.py`): Test the CLI as a user would run it (`python -m wtf_restarted`)

Some tests require administrator privileges to read all event log categories. Tests that need elevation are designed to degrade gracefully when run without it.

### One-offs and Exploratory Scripts

The `tests/one-offs/` directory is for exploratory scripts, one-time diagnostics, and proof-of-concept code. These aren't run by pytest but are included in commits to preserve context about what was investigated and why.

Scripts that prove their value graduate to either `tests/` (as proper regression tests) or `scripts/` (as reusable utilities).

## Versioning

The project uses a custom version scheme defined in `_version.py`:

- **Semantic base**: `MAJOR.MINOR.PATCH` (e.g., `0.1.1`)
- **Phase**: Per-minor feature maturity (`alpha`, `beta`, or None when stable)
- **Project phase**: Overall project maturity (`prealpha`, `alpha`, `beta`, `stable`)
- **Build metadata**: Branch, build number, date, commit hash (auto-appended by git hooks)

PyPI gets PEP 440 versions (e.g., `0.1.1a1`). The full version string with build metadata is for display and debugging.

Don't edit `__version__` directly -- it's updated by git hooks. To bump the version, edit `MAJOR`, `MINOR`, `PATCH`, and `PHASE` in `_version.py`.

## How Can I Contribute?

### Reporting Bugs

- Use [GitHub Issues](https://github.com/djdarcy/wtf-restarted/issues)
- Include the output of `wtf-restarted --version`
- Include your Windows version (`winver`)
- If possible, include the `--json` output (redact any sensitive hostnames or usernames)

### Suggesting Enhancements

- Check [existing issues](https://github.com/djdarcy/wtf-restarted/issues) and the [roadmap](https://github.com/djdarcy/wtf-restarted/issues/3) first
- Open a new issue describing the use case, not just the feature

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Run `pytest` and confirm tests pass
5. Submit a pull request

Keep PRs focused -- one feature or fix per PR. If your change touches the PowerShell engine (`investigate.ps1`), make sure the JSON contract between PS1 and Python is preserved.

### Areas Where Help is Welcome

Check issues labeled [`good first issue`](https://github.com/djdarcy/wtf-restarted/labels/good%20first%20issue) for accessible starting points. Other areas:

- **Event ID coverage**: Know of Windows events that indicate restart causes we're not checking? Open an issue or PR against `investigate.ps1`
- **Output formatting**: Improvements to the Rich terminal output
- **Documentation**: Expanding event reference docs, usage examples
- **Testing**: More test coverage, especially edge cases in verdict logic
