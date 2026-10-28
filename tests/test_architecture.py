"""Fitness tests for the layering rule: the core never reaches the I/O edge."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "arch_docs"
CORE = ["geometry", "diagram", "model", "html", "fonts"]
EDGE = {"arch_docs.adapters", "arch_docs.cli", "weasyprint", "cairosvg"}
IO_CALLS = {"open", "read_text", "write_text", "read_bytes", "write_bytes", "mkdir"}


def imports(module: str) -> set[str]:
    tree = ast.parse((SRC / f"{module}.py").read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module", CORE)
def test_core_does_not_import_the_edge(module):
    bad = {n for n in imports(module) if n in EDGE or n.split(".")[0] in EDGE}
    assert not bad, f"{module} imports {bad}"


@pytest.mark.parametrize("module", CORE)
def test_core_does_no_file_io(module):
    tree = ast.parse((SRC / f"{module}.py").read_text())
    calls = {
        n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
    }
    assert not calls & IO_CALLS, f"{module} calls {calls & IO_CALLS}"


def test_adapters_do_not_import_the_cli():
    assert "arch_docs.cli" not in imports("adapters")
