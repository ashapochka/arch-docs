import xml.etree.ElementTree as ET
from pathlib import Path

from arch_docs.fonts import fontconfig_xml


def parse(xml: str) -> ET.Element:
    # Drop the DOCTYPE line; ElementTree does not need it.
    return ET.fromstring(xml.split("\n", 2)[2] if "<!DOCTYPE" in xml else xml)


def test_keeps_system_config_and_adds_dir_and_cache():
    root = parse(fontconfig_xml(Path("/fonts"), Path("/cache")))
    assert [i.text for i in root.findall("include")] == ["/etc/fonts/fonts.conf"]
    assert [d.text for d in root.findall("dir")] == ["/fonts"]
    assert [c.text for c in root.findall("cachedir")] == ["/cache"]


def test_maps_helvetica_to_arial_by_default():
    root = parse(fontconfig_xml(Path("/f"), Path("/c")))
    aliases = [
        (a.findtext("family"), a.findtext("prefer/family"))
        for a in root.findall("alias")
    ]
    assert aliases == [("Helvetica", "Arial")]


def test_custom_aliases():
    root = parse(fontconfig_xml(Path("/f"), Path("/c"), {"Times": "Liberation Serif"}))
    assert root.findtext("alias/family") == "Times"
    assert root.findtext("alias/prefer/family") == "Liberation Serif"


def test_escapes_paths_and_names():
    xml = fontconfig_xml(Path("/a&b/<f>"), Path("/c"), {"A&B": "C<D"})
    root = parse(xml)
    assert root.findtext("dir") == "/a&b/<f>"
    assert root.findtext("alias/family") == "A&B"
