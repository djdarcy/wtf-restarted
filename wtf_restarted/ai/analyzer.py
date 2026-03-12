"""AI-enhanced diagnosis analyzer.

Orchestrates prompt building, backend invocation, and response parsing
to produce AI-powered analysis of restart evidence.
"""

import json
import re
from pathlib import Path

# Prompt template lives alongside this module
_PROMPT_DIR = Path(__file__).parent / "prompts"

# Available backends (lazy-loaded)
_BACKENDS = {
    "claude": "wtf_restarted.ai.backends.claude",
    "prompt-only": "wtf_restarted.ai.backends.prompt_only",
}


def get_backend(name="claude"):
    """Get a backend module by name."""
    if name not in _BACKENDS:
        raise ValueError(
            f"Unknown AI backend: {name!r}. "
            f"Available: {', '.join(_BACKENDS)}"
        )
    import importlib
    return importlib.import_module(_BACKENDS[name])


def check_available(backend_name="claude"):
    """Check if the specified backend is available."""
    try:
        backend = get_backend(backend_name)
        return backend.is_available()
    except (ValueError, ImportError):
        return False


def build_prompt(results):
    """
    Build the AI analysis prompt from investigation results.

    Args:
        results: dict from run_investigation()

    Returns:
        str: The complete prompt text
    """
    template_path = _PROMPT_DIR / "diagnose.md"
    template = template_path.read_text(encoding="utf-8")

    # Build a cleaned evidence dict (exclude raw_output to save tokens,
    # we'll include it separately in a dedicated section)
    evidence = _clean_for_prompt(results)
    evidence_json = json.dumps(evidence, indent=2, default=str)

    # Build dump analysis section if raw output is available
    dump_section = ""
    raw_output = (results.get("dump_analysis") or {}).get("raw_output")
    if raw_output:
        # Truncate very long kd.exe output
        lines = raw_output.splitlines()
        if len(lines) > 200:
            raw_output = "\n".join(lines[-200:])
            raw_output = f"[...truncated to last 200 lines...]\n{raw_output}"
        dump_section = (
            "\n## Crash Dump Analysis (kd.exe !analyze -v output)\n\n"
            f"```\n{raw_output}\n```\n"
        )

    return template.replace("{evidence_json}", evidence_json).replace(
        "{dump_section}", dump_section
    )


def _clean_for_prompt(results):
    """Remove raw_output and other large fields from the evidence dict."""
    cleaned = {}
    for key, value in results.items():
        if key == "dump_analysis" and isinstance(value, dict):
            # Include parsed fields, exclude raw_output
            cleaned[key] = {
                k: v for k, v in value.items() if k != "raw_output"
            }
        else:
            cleaned[key] = value
    return cleaned


def analyze(results, backend_name="claude", verbose=False, timeout=120):
    """
    Run AI analysis on investigation results.

    Args:
        results: dict from run_investigation()
        backend_name: which AI backend to use
        verbose: stream output in real-time
        timeout: seconds before timing out

    Returns:
        dict with keys:
            success: bool
            raw_response: str (full AI response text)
            sections: dict (parsed sections: what_happened, why, what_to_do, confidence)
            error: str or None
    """
    backend = get_backend(backend_name)

    if not backend.is_available():
        return {
            "success": False,
            "raw_response": "",
            "sections": {},
            "error": f"AI backend '{backend_name}' is not available",
        }

    prompt = build_prompt(results)
    success, output = backend.invoke(
        prompt, verbose=verbose, timeout=timeout
    )

    if not success:
        return {
            "success": False,
            "raw_response": output,
            "sections": {},
            "error": output,
        }

    sections = parse_response(output)

    return {
        "success": True,
        "raw_response": output,
        "sections": sections,
        "error": None,
    }


def parse_response(text):
    """
    Parse the AI response into structured sections.

    Expected format:
        What Happened:
        ...

        Why:
        ...

        What To Do:
        ...

        Confidence:
        ...

    Returns:
        dict with keys: what_happened, why, what_to_do, confidence
    """
    sections = {}

    # Pattern: section label at start of line, followed by colon, then content
    # until the next section label or end of string
    labels = [
        ("what_happened", r"What Happened:"),
        ("why", r"Why:"),
        ("what_to_do", r"What To Do:"),
        ("confidence", r"Confidence:"),
    ]

    for i, (key, pattern) in enumerate(labels):
        # Build regex: match this label, capture until next label or end
        if i < len(labels) - 1:
            next_patterns = [lbl for _, lbl in labels[i + 1:]]
            stop = "|".join(next_patterns)
            regex = rf"{pattern}\s*(.*?)(?=(?:{stop})|\Z)"
        else:
            regex = rf"{pattern}\s*(.*)"

        match = re.search(regex, text, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()

    # If structured parsing failed, store the whole response
    if not sections:
        sections["raw"] = text.strip()

    return sections
