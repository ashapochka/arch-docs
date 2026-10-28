"""`arch-docs` command line: pdf, preview and check subcommands."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from arch_docs.adapters import find_font_dir, svg_to_png, write_pdf
from arch_docs.html import markdown_to_html, title_from_markdown
from arch_docs.model import check_drawio_svg


def main(argv: Sequence[str] | None = None) -> int:
    """Run the `arch-docs` CLI and return its exit status.

    Subcommands:
    - `pdf SOURCE.md [-o OUT.pdf] [--title T] [--css FILE] [--font-dir DIR |
      --no-font-dir]`: render Markdown with its images to PDF. OUT defaults to
      SOURCE with a `.pdf` suffix; the title defaults to the first `# ` heading,
      else the file stem; the font dir defaults to the first found Arial dir.
    - `preview SVG... [--out-dir DIR] [--scale S]`: write a PNG per SVG, next
      to it unless `--out-dir` is given.
    - `check SVG...`: validate each .drawio.svg; prints `ok <file>` or
      `<file>: <problem>` per problem.

    Each written file is printed as `wrote <path>`.

    Returns 0 on success and 1 when an input file is missing or `check` finds a
    problem (messages go to stderr). Usage errors exit with status 2.
    """
    args = _parser().parse_args(argv)
    command: str = args.command
    if command == "pdf":
        return _pdf(args)
    if command == "preview":
        return _preview(args)
    return _check(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arch-docs", description="Architecture docs: diagrams and PDF."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pdf = sub.add_parser("pdf", help="render Markdown (with its images) to PDF")
    pdf.add_argument("source", type=Path)
    pdf.add_argument("-o", "--output", type=Path, help="default: SOURCE with .pdf")
    pdf.add_argument("--title", help="footer/document title; default: first # heading")
    pdf.add_argument("--css", type=Path, help="extra CSS applied after the defaults")
    fonts = pdf.add_mutually_exclusive_group()
    fonts.add_argument("--font-dir", type=Path, help="directory with Arial")
    fonts.add_argument(
        "--no-font-dir", action="store_true", help="use system fonts only"
    )

    preview = sub.add_parser("preview", help="rasterize SVGs to PNG for checking")
    preview.add_argument("svgs", nargs="+", type=Path)
    preview.add_argument("--out-dir", type=Path, help="default: next to each SVG")
    preview.add_argument("--scale", type=float, default=1.5)

    check = sub.add_parser("check", help="validate .drawio.svg files")
    check.add_argument("svgs", nargs="+", type=Path)
    return parser


def _pdf(args: argparse.Namespace) -> int:
    source: Path = args.source
    if not source.is_file():
        print(f"error: source not found: {source}", file=sys.stderr)
        return 1
    text = source.read_text(encoding="utf-8")
    title: str = args.title or title_from_markdown(text) or source.stem
    css_path: Path | None = args.css
    extra_css = css_path.read_text(encoding="utf-8") if css_path else ""
    font_dir: Path | None = (
        None if args.no_font_dir else (args.font_dir or find_font_dir())
    )
    output: Path = args.output or source.with_suffix(".pdf")
    html = markdown_to_html(text, title=title, extra_css=extra_css)
    print(f"wrote {write_pdf(html, output, base_url=source.parent, font_dir=font_dir)}")
    return 0


def _preview(args: argparse.Namespace) -> int:
    svgs: list[Path] = args.svgs
    out_dir: Path | None = args.out_dir
    status = 0
    for svg in svgs:
        stem = svg.name.removesuffix(".svg").removesuffix(".drawio")
        target = out_dir / f"{stem}.png" if out_dir else None
        try:
            print(f"wrote {svg_to_png(svg, target, scale=args.scale)}")
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            status = 1
    return status


def _check(args: argparse.Namespace) -> int:
    svgs: list[Path] = args.svgs
    status = 0
    for svg in svgs:
        try:
            problems = check_drawio_svg(svg.read_text(encoding="utf-8"))
        except OSError as e:
            problems = [f"cannot read: {e.strerror or e}"]
        if problems:
            status = 1
            for problem in problems:
                print(f"{svg}: {problem}", file=sys.stderr)
        else:
            print(f"ok {svg}")
    return status
