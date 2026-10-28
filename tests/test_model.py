from xml.sax.saxutils import quoteattr

import pytest

from arch_docs.model import check_drawio_svg, extract_model


def svg_with(mxfile: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" content={quoteattr(mxfile)}></svg>'


def mxfile(cells: str) -> str:
    return (
        '<mxfile><diagram name="d"><mxGraphModel><root><mxCell id="0"/>'
        f'<mxCell id="1" parent="0"/>{cells}</root></mxGraphModel></diagram></mxfile>'
    )


def test_extract_model_returns_embedded_mxfile(sample):
    model = extract_model(sample.render())
    assert model.startswith("<mxfile")
    assert 'id="a"' in model


def test_extract_model_rejects_non_svg():
    with pytest.raises(ValueError, match="SVG"):
        extract_model("<html></html>")


def test_extract_model_rejects_unparseable_text():
    with pytest.raises(ValueError, match="SVG"):
        extract_model("not xml")


def test_extract_model_rejects_svg_without_model():
    with pytest.raises(ValueError, match="model"):
        extract_model('<svg xmlns="http://www.w3.org/2000/svg"/>')


def test_check_accepts_generated_diagrams(sample, sequence):
    assert check_drawio_svg(sample.render()) == []
    assert check_drawio_svg(sequence.render()) == []


def test_check_reports_missing_model():
    problems = check_drawio_svg('<svg xmlns="http://www.w3.org/2000/svg"/>')
    assert len(problems) == 1 and "model" in problems[0]


def test_check_reports_unparseable_model():
    problems = check_drawio_svg(svg_with("<mxfile><broken"))
    assert len(problems) == 1 and "parse" in problems[0]


def test_check_reports_model_without_diagram():
    assert check_drawio_svg(svg_with("<mxfile/>")) == ["model has no diagram"]


def test_check_reports_diagram_without_cells():
    problems = check_drawio_svg(svg_with('<mxfile><diagram name="d"/></mxfile>'))
    assert problems == ["diagram 'd' has no cells"]


def test_check_reports_duplicate_ids():
    cells = '<mxCell id="a" vertex="1"/><mxCell id="a" vertex="1"/>'
    assert check_drawio_svg(svg_with(mxfile(cells))) == ["duplicate cell id 'a'"]


def test_check_reports_dangling_edge_ends():
    cells = '<mxCell id="a" vertex="1"/><mxCell id="e" edge="1" source="a" target="x"/>'
    assert check_drawio_svg(svg_with(mxfile(cells))) == [
        "edge 'e' target 'x' does not exist"
    ]
