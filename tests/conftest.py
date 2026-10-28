import pytest

from arch_docs.diagram import Diagram


@pytest.fixture
def sample() -> Diagram:
    """A small diagram that uses every shape and connector kind."""
    d = Diagram("sample", 600, 400)
    d.container("grp", 10, 10, 580, 380, "Group")
    d.box("a", 40, 50, 120, 50, "A\nfirst")
    d.box("b", 300, 50, 120, 50, "B & <b>", "srv", dashed=True)
    d.cylinder("db", 40, 150, 120, 60, "DB")
    d.note("n", 300, 150, 140, 50, "a note")
    d.ellipse("uc", 40, 250, 120, 50, "Use case")
    d.diamond("q", 300, 250, 100, 60, "ok?")
    d.terminal("end", 450, 260, 100, 36, "End", "err")
    d.actor("u", 500, 40, "User")
    d.classbox("cls", 450, 120, 130, None, "Store", ["get(id)", "  nested"],
               stereotype="Protocol")  # fmt: skip
    d.text(200, 350, 200, 20, "free text", italic=True, bold=True)
    d.edge("a", "right", "b", "left", "calls", via=[(230, 75)])
    d.edge("a", "bottom", "db", "top", kind="dep")
    d.edge("q", "right", "end", "left", "yes", kind="assoc")
    d.edge("cls", "bottom", "end", "top", kind="inherit")
    d.edge("b", "bottom", "n", "top", kind="return")
    return d


@pytest.fixture
def sequence() -> Diagram:
    d = Diagram("seq", 500, 300)
    d.lifeline("user", 60, 20, 280, "User", actor=True)
    d.lifeline("app", 250, 20, 280, "App")
    d.frame(20, 100, 460, 150, "alt", "[ok]")
    d.msg("user", "app", 120, "request")
    d.self_msg("app", 140, "work")
    d.divider(20, 190, 460, "[else]")
    d.msg("app", "user", 220, "reply", kind="return")
    return d
