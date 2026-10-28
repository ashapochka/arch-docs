from pathlib import Path

import pytest

from arch_docs import cli
from arch_docs.adapters import save_diagram
from arch_docs.diagram import Diagram


@pytest.fixture
def svg(tmp_path) -> Path:
    d = Diagram("one", 120, 60)
    d.box("a", 10, 10, 100, 40, "A")
    return save_diagram(d, tmp_path)


class FakePdf:
    """Records write_pdf calls instead of running WeasyPrint."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, html: str, output: Path, *, base_url: Path,
                 font_dir: Path | None = None) -> Path:  # fmt: skip
        self.calls.append(
            {"html": html, "output": output, "base_url": base_url, "font_dir": font_dir}
        )
        return output


@pytest.fixture
def fake_pdf(monkeypatch) -> FakePdf:
    fake = FakePdf()
    monkeypatch.setattr(cli, "write_pdf", fake)
    monkeypatch.setattr(cli, "find_font_dir", lambda: None)
    return fake


# ------------------------------------------------------------------- pdf
def test_pdf_defaults(tmp_path, fake_pdf, capsys):
    src = tmp_path / "arch.md"
    src.write_text("# System Design\n\ntext\n")
    assert cli.main(["pdf", str(src)]) == 0
    (call,) = fake_pdf.calls
    assert call["output"] == tmp_path / "arch.pdf"
    assert call["base_url"] == tmp_path
    assert call["font_dir"] is None
    assert "<title>System Design</title>" in str(call["html"])
    assert capsys.readouterr().out == f"wrote {tmp_path / 'arch.pdf'}\n"


def test_pdf_title_falls_back_to_stem(tmp_path, fake_pdf):
    src = tmp_path / "notes.md"
    src.write_text("no heading\n")
    cli.main(["pdf", str(src)])
    assert "<title>notes</title>" in str(fake_pdf.calls[0]["html"])


def test_pdf_options(tmp_path, fake_pdf):
    src = tmp_path / "a.md"
    src.write_text("# H\n")
    css = tmp_path / "extra.css"
    css.write_text("h1 { color: red; }")
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    out = tmp_path / "o" / "x.pdf"
    args = ["pdf", str(src), "-o", str(out), "--title", "T", "--css", str(css),
            "--font-dir", str(fonts)]  # fmt: skip
    assert cli.main(args) == 0
    (call,) = fake_pdf.calls
    assert call["output"] == out
    assert call["font_dir"] == fonts
    assert "<title>T</title>" in str(call["html"])
    assert "h1 { color: red; }" in str(call["html"])


def test_pdf_uses_found_font_dir_unless_disabled(tmp_path, fake_pdf, monkeypatch):
    src = tmp_path / "a.md"
    src.write_text("x")
    monkeypatch.setattr(cli, "find_font_dir", lambda: tmp_path)
    cli.main(["pdf", str(src)])
    cli.main(["pdf", str(src), "--no-font-dir"])
    assert [c["font_dir"] for c in fake_pdf.calls] == [tmp_path, None]


def test_pdf_missing_source(tmp_path, fake_pdf, capsys):
    assert cli.main(["pdf", str(tmp_path / "nope.md")]) == 1
    assert "nope.md" in capsys.readouterr().err
    assert fake_pdf.calls == []


def test_font_dir_options_are_exclusive(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(["pdf", "a.md", "--font-dir", str(tmp_path), "--no-font-dir"])
    assert exc.value.code == 2


def test_no_subcommand_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2


# ---------------------------------------------------------------- check
def test_check_ok(svg, capsys):
    assert cli.main(["check", str(svg)]) == 0
    assert capsys.readouterr().out == f"ok {svg}\n"


def test_check_reports_problems_and_missing_files(svg, tmp_path, capsys):
    bad = tmp_path / "bad.drawio.svg"
    bad.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    missing = tmp_path / "missing.drawio.svg"
    assert cli.main(["check", str(svg), str(bad), str(missing)]) == 1
    captured = capsys.readouterr()
    assert captured.out == f"ok {svg}\n"
    err = captured.err.splitlines()
    assert err[0].startswith(f"{bad}: ") and "model" in err[0]
    assert err[1].startswith(f"{missing}: ")


# -------------------------------------------------------------- preview
@pytest.mark.slow
def test_preview_writes_png_next_to_svg_or_into_out_dir(svg, tmp_path, capsys):
    assert cli.main(["preview", str(svg)]) == 0
    assert (tmp_path / "one.png").exists()
    out_dir = tmp_path / "pngs"
    assert (
        cli.main(["preview", str(svg), "--out-dir", str(out_dir), "--scale", "1"]) == 0
    )
    assert (out_dir / "one.png").exists()
    assert capsys.readouterr().out.splitlines() == [
        f"wrote {tmp_path / 'one.png'}",
        f"wrote {out_dir / 'one.png'}",
    ]


def test_preview_missing_file(tmp_path, capsys):
    assert cli.main(["preview", str(tmp_path / "nope.svg")]) == 1
    assert "nope.svg" in capsys.readouterr().err
