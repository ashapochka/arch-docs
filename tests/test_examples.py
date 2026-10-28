import importlib.util
import sys
from pathlib import Path

import pytest

from arch_docs.model import check_drawio_svg

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.parent.name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("script", sorted(EXAMPLES.glob("*/diagrams.py")), ids=str)
def test_example_diagrams_are_valid(script):
    diagrams = load(script).build()
    assert diagrams
    names = [d.name for d in diagrams]
    assert len(names) == len(set(names))
    for d in diagrams:
        assert check_drawio_svg(d.render()) == [], d.name
