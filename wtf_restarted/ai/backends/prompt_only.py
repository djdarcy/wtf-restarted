"""Prompt-only backend -- saves the prompt to a file for manual use."""

from datetime import datetime
from pathlib import Path


def _get_output_dir():
    """Get the wtf-restarted user data directory."""
    out_dir = Path.home() / ".wtf-restarted" / "ai"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def is_available():
    """Always available."""
    return True


def invoke(prompt, verbose=False, timeout=120):
    """
    Save prompt to a file instead of invoking an AI.

    Returns: (success: bool, output: str)
    """
    out_dir = _get_output_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    prompt_file = out_dir / f"prompt_{timestamp}.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    return False, (
        f"Prompt saved to: {prompt_file}\n"
        "Paste this prompt into an AI assistant for analysis.\n"
        "Tip: try https://chatgpt.com/g/g-Pn1omABcF-devop-it-scripting-guru"
    )
