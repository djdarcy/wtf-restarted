"""OpenAI Codex CLI backend for AI analysis."""

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


def is_available():
    """Check if Codex CLI is installed and accessible."""
    return find_cli() is not None


def find_cli():
    """Find the Codex CLI executable.

    Checks PATH first (covers npm global, winget shim, or any user config),
    then falls back to known install locations on Windows.

    Validates that the found binary is actually runnable (shims can point
    to deleted binaries).
    """
    candidates = []

    # PATH-visible installs (npm shim, winget shim, custom builds)
    path_hit = shutil.which("codex") or shutil.which("codex.exe")
    if path_hit:
        candidates.append(str(path_hit))

    # Windows-specific fallback locations
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if appdata:
            # npm global install
            candidates.append(str(Path(appdata) / "npm" / "codex.cmd"))
        if localappdata:
            # winget shim
            candidates.append(
                str(Path(localappdata) / "Microsoft" / "WinGet"
                    / "Links" / "codex.cmd")
            )

    for c in candidates:
        if not Path(c).exists():
            continue
        if _validate_cli(c):
            return c

    return None


def _validate_cli(cli_path):
    """Check that a codex binary/shim is actually runnable."""
    try:
        result = subprocess.run(
            [cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def invoke(prompt, verbose=False, timeout=120):
    """
    Invoke Codex CLI with a prompt via stdin.

    Returns: (success: bool, output: str)
    """
    codex_path = find_cli()
    if not codex_path:
        return False, (
            "Codex CLI not found. "
            "Install with: npm install -g @openai/codex"
        )

    cmd = [codex_path, "exec", "--skip-git-repo-check", "-"]

    env = os.environ.copy()

    try:
        if verbose:
            return _invoke_streaming(cmd, env, timeout, prompt)
        else:
            return _invoke_blocking(cmd, env, timeout, prompt)
    except FileNotFoundError:
        return False, f"Codex CLI not found at: {codex_path}"
    except Exception as e:
        return False, f"Error invoking Codex CLI: {e}"


def _invoke_blocking(cmd, env, timeout, prompt):
    """Run Codex CLI and capture output."""
    result = subprocess.run(
        cmd,
        env=env,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    output = result.stdout
    if result.returncode == 0:
        return True, output
    else:
        return False, (
            f"Codex CLI exited with code {result.returncode}\n"
            f"stderr: {result.stderr}"
        )


def _invoke_streaming(cmd, env, timeout, prompt):
    """Run Codex CLI with real-time output streaming."""
    process = subprocess.Popen(
        cmd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Send prompt via stdin, then close to signal EOF
    try:
        process.stdin.write(prompt)
        process.stdin.close()
    except OSError:
        pass  # Process may have exited early

    output_lines = []

    def _reader():
        for line in process.stdout:
            output_lines.append(line)
            sys.stdout.write(line)
            sys.stdout.flush()

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    try:
        start = time.time()
        while process.poll() is None:
            if time.time() - start > timeout:
                process.kill()
                process.wait()
                return False, "Codex CLI timed out"
            time.sleep(0.2)
        reader.join(timeout=5)
    except KeyboardInterrupt:
        process.kill()
        process.wait()
        return False, "Cancelled by user (Ctrl+C)"

    output = "".join(output_lines)
    if process.returncode == 0:
        return True, output
    else:
        return False, (
            f"Codex CLI exited with code {process.returncode}\n{output}"
        )
