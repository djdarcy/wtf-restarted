"""Claude Code CLI backend for AI analysis."""

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


def is_available():
    """Check if Claude Code CLI is installed and accessible."""
    return find_cli() is not None


def find_cli():
    """Find the Claude Code CLI executable."""
    candidates = [
        shutil.which("claude"),
        shutil.which("claude.exe"),
        Path.home() / ".local" / "bin" / "claude.exe",
        Path.home() / ".local" / "bin" / "claude",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def invoke(prompt, verbose=False, timeout=120):
    """
    Invoke Claude Code CLI with a prompt.

    Returns: (success: bool, output: str)
    """
    claude_path = find_cli()
    if not claude_path:
        return False, (
            "Claude Code CLI not found. "
            "Install from https://claude.ai/claude-code"
        )

    cmd = [
        claude_path,
        "--output-format", "text",
        "-p",
        prompt,
    ]

    # Remove env vars that conflict with subprocess invocation
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)

    try:
        if verbose:
            return _invoke_streaming(cmd, env, timeout)
        else:
            return _invoke_blocking(cmd, env, timeout)
    except FileNotFoundError:
        return False, f"Claude CLI not found at: {claude_path}"
    except Exception as e:
        return False, f"Error invoking Claude CLI: {e}"


def _invoke_blocking(cmd, env, timeout):
    """Run Claude CLI and capture output."""
    result = subprocess.run(
        cmd,
        env=env,
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
            f"Claude CLI exited with code {result.returncode}\n"
            f"stderr: {result.stderr}"
        )


def _invoke_streaming(cmd, env, timeout):
    """Run Claude CLI with real-time output streaming."""
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
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
                return False, "Claude CLI timed out"
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
            f"Claude CLI exited with code {process.returncode}\n{output}"
        )
