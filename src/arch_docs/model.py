"""Read back and validate the draw.io model embedded in a .drawio.svg file."""

import xml.etree.ElementTree as ET
from collections import Counter

_SVG_TAG = "{http://www.w3.org/2000/svg}svg"


def extract_model(svg_text: str) -> str:
    """Return the draw.io `<mxfile>` XML embedded in a .drawio.svg document.

    Raises:
        ValueError: if the text is not an SVG document, or the SVG carries no
            embedded model.

    Implementation notes:
        draw.io stores the model, XML-escaped, in the root element's `content`
        attribute. Compressed models (base64 + deflate, written by older
        draw.io versions) are returned as stored, not inflated.
    """
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        raise ValueError(f"not an SVG document: {e}") from e
    if root.tag not in (_SVG_TAG, "svg"):
        raise ValueError(f"not an SVG document: root element is <{root.tag}>")
    content = root.get("content")
    if not content:
        raise ValueError("SVG has no embedded draw.io model (no content attribute)")
    return content


def check_drawio_svg(svg_text: str) -> list[str]:
    """Return a list of problems with a .drawio.svg document; empty means valid.

    Reports, one message each:
    - a missing or unparseable embedded model;
    - a model with no diagram, or a diagram with no cells;
    - duplicate cell ids;
    - an edge whose source or target names a cell that does not exist.
    """
    try:
        model = extract_model(svg_text)
    except ValueError as e:
        return [str(e)]
    try:
        mxfile = ET.fromstring(model)
    except ET.ParseError as e:
        return [f"cannot parse embedded model: {e}"]
    diagrams = mxfile.findall("diagram")
    if not diagrams:
        return ["model has no diagram"]
    problems: list[str] = []
    for diagram in diagrams:
        cells = diagram.findall("./mxGraphModel/root/mxCell")
        if not cells:
            problems.append(f"diagram {diagram.get('name')!r} has no cells")
            continue
        counts = Counter(c.get("id") for c in cells)
        problems += [f"duplicate cell id {i!r}" for i, n in counts.items() if n > 1]
        for cell in cells:
            for end in ("source", "target"):
                ref = cell.get(end)
                if ref is not None and ref not in counts:
                    problems.append(
                        f"edge {cell.get('id')!r} {end} {ref!r} does not exist"
                    )
    return problems
