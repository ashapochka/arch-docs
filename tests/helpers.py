import xml.etree.ElementTree as ET


def model_root(svg_text: str) -> ET.Element:
    """Parse the mxGraphModel <root> embedded in a rendered .drawio.svg."""
    content = ET.fromstring(svg_text).get("content")
    assert content is not None
    root = ET.fromstring(content).find("./diagram/mxGraphModel/root")
    assert root is not None
    return root
