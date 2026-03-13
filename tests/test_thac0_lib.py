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


class TestInitOutput:
    """init_output/get_output singleton pattern."""

    def test_init_and_get(self):
        om = init_output(verbosity=1)
        assert om is get_output()
        assert om.verbosity == 1
