import xml.etree.ElementTree as ET

import pytest
from helpers import model_root

from arch_docs.diagram import Diagram

SVG_NS = "{http://www.w3.org/2000/svg}"


def test_render_is_wellformed_svg_with_declared_size(sample):
    svg = ET.fromstring(sample.render())
    assert svg.tag == f"{SVG_NS}svg"
    assert (svg.get("width"), svg.get("height")) == ("600px", "400px")


def test_render_embeds_one_named_diagram(sample):
    mxfile = ET.fromstring(ET.fromstring(sample.render()).get("content") or "")
    diagrams = mxfile.findall("diagram")
    assert [d.get("name") for d in diagrams] == ["sample"]


def test_every_shape_key_is_a_model_cell(sample):
    ids = {c.get("id") for c in model_root(sample.render())}
    assert set(sample.shapes) <= ids


def test_cell_ids_are_unique(sample, sequence):
    for d in (sample, sequence):
        ids = [c.get("id") for c in model_root(d.render())]
        assert len(ids) == len(set(ids))


def test_generated_ids_start_with_underscore(sample):
    ids = {c.get("id") or "" for c in model_root(sample.render())}
    generated = ids - set(sample.shapes) - {"0", "1"}
    assert generated
    assert all(i.startswith("_") for i in generated)


def test_edges_reference_their_shapes(sample):
    edges = [c for c in model_root(sample.render()) if c.get("edge") == "1"]
    assert {(e.get("source"), e.get("target")) for e in edges} == {
        ("a", "b"),
        ("a", "db"),
        ("q", "end"),
        ("cls", "end"),
        ("b", "n"),
    }


def test_edge_waypoints_are_in_the_model(sample):
    edge = next(c for c in model_root(sample.render()) if c.get("source") == "a"
                and c.get("target") == "b")  # fmt: skip
    points = edge.findall("./mxGeometry/Array/mxPoint")
    assert [(p.get("x"), p.get("y")) for p in points] == [("230", "75")]


def test_labels_are_escaped_in_both_views(sample):
    out = sample.render()
    assert "B &amp; &lt;b&gt;" in out  # SVG text
    values = [c.get("value") for c in model_root(out)]
    assert "<b>B &amp; &lt;b&gt;</b>" in values  # draw.io HTML label, first line bold


def test_multiline_label_becomes_br_separated_html(sample):
    values = [c.get("value") for c in model_root(sample.render())]
    assert "<b>A</b><br>first" in values


def test_classbox_auto_height_and_keeps_indentation(sample):
    assert sample.shapes["cls"].h == 4 + 2 * 14 + 5 + 2 * 14 + 8
    assert "  nested" in sample.render()


def test_dashed_markers_do_not_inherit_dashes(sample):
    defs = ET.fromstring(sample.render()).find(f"{SVG_NS}defs")
    assert defs is not None
    for marker_id in ("open", "tri"):
        marker = defs.find(f"{SVG_NS}marker[@id='{marker_id}']")
        assert marker is not None
        path = marker.find(f"{SVG_NS}path")
        assert path is not None and path.get("stroke-dasharray") == "none"


def test_render_is_deterministic(sample):
    assert sample.render() == sample.render()


def test_sequence_messages_run_between_lifeline_centres(sequence):
    svg = ET.fromstring(sequence.render())
    (line,) = [
        el for el in svg.iter(f"{SVG_NS}line") if el.get("y1") == el.get("y2") == "120"
    ]
    assert (float(line.get("x1", "")), float(line.get("x2", ""))) == (60, 250)
    assert sequence.shapes["app"].cx == 250


@pytest.mark.parametrize("name", ["", "has space", "../up", "_hidden", "a/b"])
def test_rejects_unsafe_names(name):
    with pytest.raises(ValueError, match="name"):
        Diagram(name, 100, 100)


@pytest.mark.parametrize("size", [(0, 100), (100, -1)])
def test_rejects_non_positive_size(size):
    with pytest.raises(ValueError, match="size"):
        Diagram("ok", *size)


def test_rejects_duplicate_key():
    d = Diagram("d", 100, 100)
    d.box("a", 0, 0, 10, 10, "A")
    with pytest.raises(ValueError, match="'a'"):
        d.ellipse("a", 0, 0, 10, 10, "again")
    assert d.shapes["a"].w == 10


@pytest.mark.parametrize("key", ["", "_e1"])
def test_rejects_empty_or_reserved_key(key):
    d = Diagram("d", 100, 100)
    with pytest.raises(ValueError, match="key"):
        d.box(key, 0, 0, 10, 10, "A")
    assert d.shapes == {}


def test_edge_to_unknown_shape_raises_keyerror_naming_it():
    d = Diagram("d", 100, 100)
    d.box("a", 0, 0, 10, 10, "A")
    with pytest.raises(KeyError, match="'nope'"):
        d.edge("a", "right", "nope", "left")


def test_message_from_unknown_lifeline_raises_keyerror():
    d = Diagram("d", 100, 100)
    with pytest.raises(KeyError, match="'ghost'"):
        d.self_msg("ghost", 10, "x")
