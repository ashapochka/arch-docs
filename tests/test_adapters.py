import os

import pytest
from pypdf import PdfReader

from arch_docs.adapters import find_font_dir, save_diagram, svg_to_png, write_pdf
from arch_docs.diagram import Diagram
from arch_docs.html import markdown_to_html

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def tiny() -> Diagram:
    d = Diagram("tiny", 120, 60)
    d.box("a", 10, 10, 100, 40, "A")
    return d


# ------------------------------------------------------------ save_diagram
def test_save_diagram_creates_dir_and_writes_named_file(tmp_path):
    out = tmp_path / "new" / "dir"
    path = save_diagram(tiny(), out)
    assert path == out / "tiny.drawio.svg"
    assert path.read_text(encoding="utf-8") == tiny().render()


def test_save_diagram_overwrites_and_is_byte_stable(tmp_path):
    first = save_diagram(tiny(), tmp_path).read_bytes()
    (tmp_path / "tiny.drawio.svg").write_text("old")
    assert save_diagram(tiny(), tmp_path).read_bytes() == first


# ----------------------------------------------------------- find_font_dir
def test_find_font_dir_returns_first_dir_with_arial(tmp_path):
    empty, upper, lower = tmp_path / "e", tmp_path / "u", tmp_path / "l"
    for d in (empty, upper, lower):
        d.mkdir()
    (upper / "ARIAL.TTF").write_bytes(b"")
    (lower / "arial.ttf").write_bytes(b"")
    assert find_font_dir([tmp_path / "missing", empty, upper, lower]) == upper


def test_find_font_dir_none_when_no_candidate_has_arial(tmp_path):
    (tmp_path / "arialbd.ttf").write_bytes(b"")
    assert find_font_dir([tmp_path, tmp_path / "missing"]) is None


# -------------------------------------------------------------- svg_to_png
@pytest.mark.slow
def test_svg_to_png_defaults_next_to_svg(tmp_path):
    svg = save_diagram(tiny(), tmp_path)
    png = svg_to_png(svg)
    assert png == tmp_path / "tiny.png"
    assert png.read_bytes().startswith(PNG_MAGIC)


@pytest.mark.slow
def test_svg_to_png_plain_svg_suffix_and_explicit_target(tmp_path):
    svg = tmp_path / "x.svg"
    svg.write_text(tiny().render())
    assert svg_to_png(svg) == tmp_path / "x.png"
    target = tmp_path / "out" / "y.png"
    assert svg_to_png(svg, target, scale=1) == target
    assert target.read_bytes().startswith(PNG_MAGIC)


def test_svg_to_png_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        svg_to_png(tmp_path / "nope.svg")


@pytest.mark.parametrize("scale", [0, -1])
def test_svg_to_png_rejects_non_positive_scale(tmp_path, scale):
    svg = save_diagram(tiny(), tmp_path)
    with pytest.raises(ValueError, match="scale"):
        svg_to_png(svg, scale=scale)


# --------------------------------------------------------------- write_pdf
@pytest.mark.slow
def test_write_pdf_embeds_relative_images(tmp_path):
    save_diagram(tiny(), tmp_path / "diagrams")
    html = markdown_to_html("![tiny](diagrams/tiny.drawio.svg)\n", title="T")
    out = write_pdf(html, tmp_path / "out" / "doc.pdf", base_url=tmp_path)
    assert out == tmp_path / "out" / "doc.pdf"
    (page,) = PdfReader(out).pages
    # The diagram is embedded as vector graphics: its label is real text.
    assert "A" in page.extract_text()


def test_write_pdf_missing_font_dir(tmp_path):
    with pytest.raises(FileNotFoundError, match="font"):
        write_pdf("<p>x</p>", tmp_path / "d.pdf", base_url=tmp_path,
                  font_dir=tmp_path / "missing")  # fmt: skip
    assert not (tmp_path / "d.pdf").exists()


@pytest.mark.slow
def test_write_pdf_restores_fontconfig_env(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    before = os.environ.get("FONTCONFIG_FILE")
    write_pdf("<p>x</p>", tmp_path / "d.pdf", base_url=tmp_path, font_dir=fonts)
    assert os.environ.get("FONTCONFIG_FILE") == before
