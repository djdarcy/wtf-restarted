"""AI-enhanced diagnosis analyzer.

Orchestrates prompt building, backend invocation, and response parsing
to produce AI-powered analysis of restart evidence.

Includes response caching to avoid redundant API calls when the same
investigation data is analyzed multiple times (Issue #18).
"""

import hashlib
import json
import re
import time
from pathlib import Path

# Prompt template lives alongside this module
_PROMPT_DIR = Path(__file__).parent / "prompts"

# Cache directory and TTL
_CACHE_DIR = Path.home() / ".wtf-restarted" / "cache"
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

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


def _cache_stable_fields(results):
    """Build a semantic fingerprint of investigation findings for cache key.

    Uses event counts + sorted timestamps as event identity rather than
    raw event payloads. This means --hours 60 and --hours 80 produce the
    same cache key when they find the same events (Issue #20).

    Excludes context_window, windows_update, boot_sequence, and
    app_crashes (supporting context that doesn't drive the diagnosis).
    """
    fingerprint = {}

    # Verdict type is the primary classifier
    fingerprint["verdict_type"] = results.get("verdict", {}).get("type")

    # Count and identify events by diagnosis-relevant category
    events = results.get("events", {})
    for category in ("kernel_power_41", "event_6008", "shutdown_initiator",
                     "bugcheck", "whea", "gpu_events"):
        items = events.get(category, [])
        fingerprint[f"{category}_count"] = len(items)
        fingerprint[f"{category}_times"] = sorted(
            e.get("time", "") for e in items
        )

    # Dump analysis findings (not paths, just results)
    da = results.get("dump_analysis", {})
    if da.get("performed"):
        fingerprint["dump_bugcheck"] = da.get("bugcheck_code")
        fingerprint["dump_module"] = da.get("module")
        fingerprint["dump_bucket"] = da.get("bucket")
    else:
        fingerprint["dump_performed"] = False

    # Evidence flags as booleans (not strings)
    evidence = results.get("evidence", {})
    fingerprint["evidence"] = {
        "dirty_shutdown": bool(evidence.get("dirty_shutdown")),
        "bugcheck": bool(evidence.get("bugcheck")),
        "whea_error": bool(evidence.get("whea_error")),
        "crash_dump_exists": bool(evidence.get("crash_dump_exists")),
    }

    return fingerprint


def _cache_key(results, backend_name):
    """Generate a cache key from investigation results and backend.

    Hashes only stable event-driven fields so that two runs with the
    same restart events produce the same key, even if uptime or other
    ephemeral system state has changed.
    """
    stable = _cache_stable_fields(results)
    payload = json.dumps(stable, sort_keys=True, default=str) + "\n" + backend_name
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _cache_read(cache_key, backend_name):
    """Try to read a cached AI response. Returns the result dict or None."""
    cache_file = _CACHE_DIR / f"ai_{backend_name}_{cache_key}.json"
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        # Check TTL
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > _CACHE_TTL_SECONDS:
            cache_file.unlink(missing_ok=True)
            return None
        result = data.get("result")
        if result:
            result["cached"] = True
            result["cached_at"] = cached_at
        return result
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _cache_write(cache_key, backend_name, result):
    """Write an AI response to the cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"ai_{backend_name}_{cache_key}.json"
        data = {
            "cached_at": time.time(),
            "backend": backend_name,
            "result": result,
        }
        cache_file.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError:
        pass  # Cache write failure is non-fatal


def analyze(results, backend_name="claude", verbose=False, timeout=120, refresh=False):
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
    # prompt-only backend is never cached (it saves a file, not an API call)
    skip_cache = backend_name == "prompt-only"

    # Check cache first (unless --ai-refresh or prompt-only)
    if not refresh and not skip_cache:
        key = _cache_key(results, backend_name)
        cached = _cache_read(key, backend_name)
        if cached:
            return cached

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

    result = {
        "success": True,
        "raw_response": output,
        "sections": sections,
        "error": None,
    }

    # Cache successful results
    if not skip_cache:
        _cache_write(key, backend_name, result)

    return result


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
