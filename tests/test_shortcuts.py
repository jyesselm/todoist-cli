"""ShortcutExpander behaviour with the real shortcut scheme."""

import pytest

from todoist_cli.models import Project, ShortcutConfig
from todoist_cli.shortcuts import ShortcutExpander


@pytest.fixture
def expander() -> ShortcutExpander:
    cfg = ShortcutConfig(
        labels={"q": "quick", "w": "waiting"},
        projects={"r": "🔬 Research", "u": "👥 Students"},
        priorities={"u": "p1"},
    )
    return ShortcutExpander(cfg, [Project(id="p1", name="🔬 Research")])


def test_label_shortcut(expander: ShortcutExpander) -> None:
    assert expander.expand("call @q") == "call @quick"


def test_project_shortcut(expander: ShortcutExpander) -> None:
    assert expander.expand("call #r") == "call #🔬 Research"


def test_unknown_shortcuts_untouched(expander: ShortcutExpander) -> None:
    assert expander.expand("call @zzz #zzz") == "call @zzz #zzz"


def test_native_priority_untouched(expander: ShortcutExpander) -> None:
    assert expander.expand("call p1 p3") == "call p1 p3"


def test_expand_project_by_stripped_name(expander: ShortcutExpander) -> None:
    assert expander.expand_project("research") == "🔬 Research"
    assert expander.expand_project("nothing") == "nothing"


def test_expand_priority(expander: ShortcutExpander) -> None:
    assert expander.expand_priority("u") == "p1"
    assert expander.expand_priority("p3") == "p3"
    assert expander.expand_priority("zz") is None
    assert expander.list_shortcuts()["labels"] == {"q": "quick", "w": "waiting"}
