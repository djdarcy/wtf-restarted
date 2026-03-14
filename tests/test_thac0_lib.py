"""Sanity tests for the ported THAC0 libraries."""

import sys
from io import StringIO

from wtf_restarted.lib.log_lib import (
    OutputManager,
    init_output,
    get_output,
)
from wtf_restarted.lib.log_lib.levels import (
    DEBUG, CONFIG, TIMING, DEFAULT, MINIMAL, WARNING, ERROR, NOTHING,
)
from wtf_restarted.lib.log_lib.channels import (
    ChannelConfig,
    parse_channel_spec,
    KNOWN_CHANNELS,
)
from wtf_restarted.lib.log_lib.hints import Hint, register_hint, get_hint
from wtf_restarted.lib.core_lib import Action, Plan
from wtf_restarted.lib.help_lib import HelpContent, HelpSection, HelpBuilder


class TestLevels:
    """THAC0 level constants are correctly ordered."""

    def test_level_ordering(self):
        assert NOTHING < ERROR < WARNING < MINIMAL < DEFAULT < TIMING < CONFIG < DEBUG

    def test_default_is_zero(self):
        assert DEFAULT == 0

    def test_nothing_is_hard_wall(self):
        assert NOTHING == -4


class TestOutputManager:
    """OutputManager emits messages based on verbosity threshold."""

    def test_default_verbosity(self):
        om = OutputManager(verbosity=0, file=StringIO())
        assert om.verbosity == 0

    def test_emit_at_default(self):
        buf = StringIO()
        om = OutputManager(verbosity=0, file=buf)
        om.emit(DEFAULT, "hello")
        assert "hello" in buf.getvalue()

    def test_suppressed_above_threshold(self):
        buf = StringIO()
        om = OutputManager(verbosity=0, file=buf)
        om.emit(TIMING, "should not appear")
        assert buf.getvalue() == ""

    def test_verbose_shows_more(self):
        buf = StringIO()
        om = OutputManager(verbosity=1, file=buf)
        om.emit(TIMING, "timing info")
        assert "timing info" in buf.getvalue()

    def test_nothing_blocks_everything(self):
        buf = StringIO()
        om = OutputManager(verbosity=NOTHING, file=buf)
        om.emit(ERROR, "error msg")
        assert buf.getvalue() == ""

    def test_error_at_error_level(self):
        buf = StringIO()
        om = OutputManager(verbosity=ERROR, file=buf)
        om.error("bad thing")
        assert "bad thing" in buf.getvalue()

    def test_channel_override(self):
        buf = StringIO()
        om = OutputManager(verbosity=0, channel_overrides={"trace": 3}, file=buf)
        om.emit(DEBUG, "trace output", channel="trace")
        assert "trace output" in buf.getvalue()

    def test_channel_active(self):
        om = OutputManager(verbosity=0, channel_overrides={"trace": -1})
        assert om.channel_active("trace") is False
        assert om.channel_active("general") is True


class TestChannelSpec:
    """Channel spec parsing."""

    def test_name_only(self):
        cfg = parse_channel_spec("timing")
        assert cfg.name == "timing"
        assert cfg.level == 0

    def test_name_and_level(self):
        cfg = parse_channel_spec("timing:2")
        assert cfg.name == "timing"
        assert cfg.level == 2

    def test_with_destination(self):
        cfg = parse_channel_spec("timing::stderr")
        assert cfg.name == "timing"
        assert cfg.destination == "stderr"

    def test_windows_drive_letter(self):
        cfg = parse_channel_spec("timing::file:C:\\logs\\out.log")
        assert cfg.location == "C:\\logs\\out.log"


class TestHints:
    """Hint registration and lookup."""

    def test_register_and_get(self):
        h = Hint(id="test.sanity", message="This is a test hint")
        register_hint(h)
        found = get_hint("test.sanity")
        assert found is not None
        assert found.message == "This is a test hint"

    def test_missing_hint(self):
        assert get_hint("nonexistent.hint.id") is None


class TestCoreLib:
    """Core types are importable and functional."""

    def test_plan_creation(self):
        p = Plan(command="diagnose")
        assert p.command == "diagnose"
        assert p.has_changes() is False

    def test_action_creation(self):
        a = Action(
            id="test:check:uptime",
            category="test",
            operation="check",
            target="uptime",
            description="Check system uptime",
        )
        assert a.id == "test:check:uptime"


class TestHelpLib:
    """Help library smoke test."""

    def test_help_content(self):
        hc = HelpContent(
            id="basic.diagnose",
            command="{prog}",
            description="Run basic restart diagnosis",
        )
        assert "diagnosis" in hc.description

    def test_help_section(self):
        s = HelpSection(id="basics", title="Basic Usage")
        s.add_item(HelpContent(
            id="basic.diagnose",
            command="{prog}",
            description="Diagnose last restart",
        ))
        assert len(s.items) == 1

    def test_help_builder(self):
        b = HelpBuilder(prog="wtf-restarted")
        s = HelpSection(id="basics", title="Basics")
        s.add_item(HelpContent(
            id="basic.run",
            command="{prog}",
            description="Run diagnosis",
        ))
        b.add_section(s)
        output = b.build_minimal_help()
        assert "wtf-restarted" in output


class TestRendererResolution:
    """Phase 3: three-layer renderer resolution in emit()."""

    def test_per_call_render_wins(self):
        """Layer 1: render= callable takes priority over everything."""
        buf = StringIO()
        called = []
        om = OutputManager(verbosity=0, file=buf, renderer=lambda t: called.append(('global', t)))
        result = om.emit(0, "ignored", render=lambda: called.append('per-call'))
        assert result is True
        assert called == ['per-call']

    def test_channel_renderer_wins_over_global(self):
        """Layer 2: per-channel renderer takes priority over global."""
        called = []
        om = OutputManager(
            verbosity=0,
            file=StringIO(),
            renderer=lambda t: called.append(('global', t)),
            channel_renderers={'system': lambda: called.append('channel')},
        )
        om.emit(0, "ignored", channel='system')
        assert called == ['channel']

    def test_global_renderer_used(self):
        """Layer 3: global default_renderer used when no per-call/channel."""
        called = []
        om = OutputManager(
            verbosity=0,
            file=StringIO(),
            renderer=lambda t: called.append(('global', t)),
        )
        om.emit(0, "hello world")
        assert called == [('global', 'hello world')]

    def test_builtin_fallback(self):
        """Layer 4: built-in print() when no renderers set."""
        buf = StringIO()
        om = OutputManager(verbosity=0, file=buf)
        om.emit(0, "fallback text")
        assert "fallback text" in buf.getvalue()

    def test_emit_returns_bool(self):
        """emit() returns True when shown, False when gated."""
        buf = StringIO()
        om = OutputManager(verbosity=0, file=buf)
        assert om.emit(0, "shown") is True
        assert om.emit(TIMING, "gated") is False

    def test_emit_returns_false_at_wall(self):
        """emit() returns False at hard wall (-4)."""
        om = OutputManager(verbosity=NOTHING, file=StringIO())
        assert om.emit(ERROR, "blocked") is False

    def test_type_check_on_fallback(self):
        """Built-in fallback raises TypeError for non-str messages."""
        import pytest
        om = OutputManager(verbosity=0, file=StringIO())
        with pytest.raises(TypeError, match="must be str"):
            om.emit(0, 42)

    def test_none_message_with_render(self):
        """render= works without a message string."""
        called = []
        om = OutputManager(verbosity=0, file=StringIO())
        result = om.emit(0, render=lambda: called.append('rendered'))
        assert result is True
        assert called == ['rendered']


class TestStrictChannels:
    """Phase 3: strict channel validation."""

    def test_strict_rejects_unknown(self):
        import pytest
        om = OutputManager(
            verbosity=0,
            file=StringIO(),
            known_channels={'general', 'system'},
            strict_channels=True,
        )
        with pytest.raises(ValueError, match="Unknown channel 'typo'"):
            om.emit(0, "oops", channel='typo')

    def test_strict_allows_known(self):
        buf = StringIO()
        om = OutputManager(
            verbosity=0,
            file=buf,
            known_channels={'general', 'system'},
            strict_channels=True,
        )
        result = om.emit(0, "ok", channel='system')
        assert result is True

    def test_non_strict_allows_anything(self):
        buf = StringIO()
        om = OutputManager(verbosity=0, file=buf, strict_channels=False)
        result = om.emit(0, "ok", channel='anything_goes')
        assert result is True


class TestIsLevelActive:
    """Phase 3: is_level_active() generalization."""

    def test_default_level_active(self):
        om = OutputManager(verbosity=0)
        assert om.is_level_active(0) is True
        assert om.is_level_active(-1) is True

    def test_above_threshold_inactive(self):
        om = OutputManager(verbosity=0)
        assert om.is_level_active(1) is False

    def test_channel_override_respected(self):
        om = OutputManager(verbosity=0, channel_overrides={'debug': 3})
        assert om.is_level_active(3, 'debug') is True
        assert om.is_level_active(3, 'general') is False

    def test_wall_blocks_all(self):
        om = OutputManager(verbosity=NOTHING)
        assert om.is_level_active(-3) is False

    def test_channel_active_uses_is_level_active(self):
        om = OutputManager(verbosity=0, channel_overrides={'trace': -1})
        assert om.channel_active('trace') is False
        assert om.channel_active('general') is True
        assert om.is_level_active(0, 'trace') is False


class TestInitOutput:
    """init_output/get_output singleton pattern."""

    def test_init_and_get(self):
        om = init_output(verbosity=1)
        assert om is get_output()
        assert om.verbosity == 1

    def test_init_with_renderer(self):
        called = []
        om = init_output(verbosity=0, renderer=lambda t: called.append(t))
        assert om.default_renderer is not None
        om.emit(0, "test")
        assert called == ["test"]

    def test_init_with_strict_channels(self):
        import pytest
        om = init_output(
            verbosity=0,
            known_channels={'general', 'system'},
            strict_channels=True,
        )
        assert om.strict_channels is True
        with pytest.raises(ValueError):
            om.emit(0, "bad", channel='typo')
