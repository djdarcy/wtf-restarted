"""Custom spinner themes for Rich console status indicators.

Each theme is a dict with 'interval' (ms) and 'frames' (list of single chars).
Use make_spinner() to create a Rich Spinner from a theme name.

Usage:
    from wtf_restarted.output.spinners import make_spinner

    spinner = make_spinner("star-breathe", style="bold blue")
"""

# -- Star family: point -> cross -> star -> burst -> breathe back --

SPINNERS = {
    # 6 frames, Rich's built-in star set -- smooth same-weight morph
    "star-simple": {
        "interval": 70,
        "frames": list("\u2736\u2738\u2739\u273a\u2739\u2737"),
        # ✶ ✸ ✹ ✺ ✹ ✷
    },
    # 8 frames, clean and fast
    "star-breathe": {
        "interval": 80,
        "frames": list("\u00b7\u271b\u2726\u2739\u273a\u2739\u2726\u271b"),
        # · ✛ ✦ ✹ ✺ ✹ ✦ ✛
    },
    # 12 frames, adds thin cross and simple star
    "star-crescendo": {
        "interval": 80,
        "frames": list("\u00b7\u2719\u271b\u2726\u2736\u2739\u273a\u2739\u2736\u2726\u271b\u2719"),
        # · ✙ ✛ ✦ ✶ ✹ ✺ ✹ ✶ ✦ ✛ ✙
    },
    # 16 frames, full crescendo with asterisk peak
    "star-full": {
        "interval": 70,
        "frames": list("\u00b7\u2719\u271b\u2726\u2736\u2738\u2739\u273a\u273b\u273a\u2739\u2738\u2736\u2726\u271b\u2719"),
        # · ✙ ✛ ✦ ✶ ✸ ✹ ✺ ✻ ✺ ✹ ✸ ✶ ✦ ✛ ✙
    },

    # -- Dot family: minimal, works everywhere --

    # 6 frames, subtle dot pulse
    "dot-pulse": {
        "interval": 120,
        "frames": list("\u00b7\u2219\u2022\u25cf\u2022\u2219"),
        # · ∙ • ● • ∙
    },

    # -- Cross family: rotational feel --

    # 8 frames, cross morphing
    "cross-morph": {
        "interval": 100,
        "frames": list("\u253c\u2719\u271b\u271c\u2722\u271c\u271b\u2719"),
        # ┼ ✙ ✛ ✜ ✢ ✜ ✛ ✙
    },

    # -- Diamond family: angular shapes --

    # 8 frames, diamond to star
    "diamond-star": {
        "interval": 90,
        "frames": list("\u00b7\u2726\u2727\u2736\u2737\u2736\u2727\u2726"),
        # · ✦ ✧ ✶ ✷ ✶ ✧ ✦
    },

    # -- Sparkle family: decorative, high visual interest --

    # 10 frames, sparkle burst
    "sparkle": {
        "interval": 80,
        "frames": list("\u00b7\u2726\u2736\u2738\u273b\u273a\u2749\u273a\u273b\u2738"),
        # · ✦ ✶ ✸ ✻ ✺ ❉ ✺ ✻ ✸
    },

    # -- Minimal family: for quiet/professional contexts --

    # 4 frames, just a blinking dot
    "dot-blink": {
        "interval": 300,
        "frames": [" ", "\u00b7", "\u2219", "\u00b7"],
        #   · ∙ ·
    },
    # 6 frames, gentle arc
    "arc": {
        "interval": 100,
        "frames": list("\u25dc\u25e0\u25dd\u25de\u25e1\u25df"),
        # ◜ ◠ ◝ ◞ ◡ ◟
    },
}

# -- Progress bar family: for use when endpoint is known --
# These cycle indefinitely but visually suggest forward motion.
# For real progress tracking, use rich.progress.Progress instead.

PROGRESS_BARS = {
    # Filling blocks
    "bar-fill": {
        "interval": 120,
        "frames": [
            "\u25b0\u25b1\u25b1\u25b1\u25b1\u25b1\u25b1",
            "\u25b0\u25b0\u25b1\u25b1\u25b1\u25b1\u25b1",
            "\u25b0\u25b0\u25b0\u25b1\u25b1\u25b1\u25b1",
            "\u25b0\u25b0\u25b0\u25b0\u25b1\u25b1\u25b1",
            "\u25b0\u25b0\u25b0\u25b0\u25b0\u25b1\u25b1",
            "\u25b0\u25b0\u25b0\u25b0\u25b0\u25b0\u25b1",
            "\u25b0\u25b0\u25b0\u25b0\u25b0\u25b0\u25b0",
        ],
        # ▰▱▱▱▱▱▱ -> ▰▰▰▰▰▰▰
    },
    # Growing vertical blocks
    "bar-grow": {
        "interval": 100,
        "frames": ["\u2581", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2586", "\u2585"],
        # ▁ ▃ ▄ ▅ ▆ ▇ ▆ ▅
    },
    # Sliding arrow
    "bar-arrow": {
        "interval": 100,
        "frames": [
            "\u25b9\u25b9\u25b9\u25b9\u25b9",
            "\u25b8\u25b9\u25b9\u25b9\u25b9",
            "\u25b9\u25b8\u25b9\u25b9\u25b9",
            "\u25b9\u25b9\u25b8\u25b9\u25b9",
            "\u25b9\u25b9\u25b9\u25b8\u25b9",
            "\u25b9\u25b9\u25b9\u25b9\u25b8",
        ],
        # ▹▹▹▹▹ -> ▸ slides across
    },
}

# Default spinner for the application
DEFAULT_SPINNER = "star-breathe"


def register_spinners():
    """Register all custom spinners into Rich's internal spinner registry.

    Must be called before using spinner names with console.status() or Spinner().
    Safe to call multiple times (idempotent).
    """
    from rich._spinners import SPINNERS as RICH_SPINNERS

    all_themes = {**SPINNERS, **PROGRESS_BARS}
    for name, theme in all_themes.items():
        if name not in RICH_SPINNERS:
            RICH_SPINNERS[name] = theme
