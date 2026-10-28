"""I/O edge: files, fonts on disk, WeasyPrint and CairoSVG.

Everything that touches the filesystem or a rendering library lives here; the
core modules (geometry, diagram, model, html, fonts) only build strings.
"""

import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from arch_docs.diagram import Diagram
from arch_docs.fonts import fontconfig_xml

DEFAULT_FONT_DIRS: tuple[Path, ...] = (
    Path("/mnt/c/Windows/Fonts"),  # WSL
    Path("/usr/share/fonts/truetype/msttcorefonts"),  # Debian/Ubuntu ttf-mscorefonts
    Path("/Library/Fonts"),  # macOS
)


def save_diagram(diagram: Diagram, out_dir: Path) -> Path:
    """Write `diagram` to `out_dir/<name>.drawio.svg` and return that path.

    Creates `out_dir` if needed and overwrites an existing file. The file is
    UTF-8 and byte-identical across runs for the same diagram.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{diagram.name}.drawio.svg"
    path.write_text(diagram.render(), encoding="utf-8")
    return path


def find_font_dir(candidates: Iterable[Path] = DEFAULT_FONT_DIRS) -> Path | None:
    """Return the first candidate directory that contains Arial, else None.

    A directory counts when it holds a file named `arial.ttf`, in any letter
    case. Missing candidates are skipped.
    """
    for directory in candidates:
        if directory.is_dir() and any(
            f.name.lower() == "arial.ttf" for f in directory.iterdir()
        ):
            return directory
    return None


def write_pdf(
    html: str,
    output: Path,
    *,
    base_url: Path,
    font_dir: Path | None = None,
) -> Path:
    """Render `html` to a PDF at `output` and return `output`.

    Relative links and images resolve against `base_url`. When `font_dir` is
    given, its fonts are available and Helvetica resolves to Arial. Creates the
    parent directory of `output` if needed.

    Raises:
        FileNotFoundError: if `font_dir` is given but is not a directory.

    Implementation notes:
        WeasyPrint is imported lazily, after `FONTCONFIG_FILE` points at a
        temporary config from `fonts.fontconfig_xml`; the variable is restored
        afterwards. fontconfig reads it once per process, so the first PDF
        rendered in a process decides the font setup for later ones.
    """
    if font_dir is not None and not font_dir.is_dir():
        raise FileNotFoundError(f"font directory not found: {font_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        previous = os.environ.get("FONTCONFIG_FILE")
        if font_dir is not None:
            conf = Path(tmp) / "fonts.conf"
            conf.write_text(fontconfig_xml(font_dir, Path(tmp)), encoding="utf-8")
            os.environ["FONTCONFIG_FILE"] = str(conf)
        try:
            from weasyprint import HTML  # pyright: ignore[reportMissingTypeStubs]

            document: Any = HTML(string=html, base_url=str(base_url))
            document.write_pdf(output)
        finally:
            if previous is None:
                os.environ.pop("FONTCONFIG_FILE", None)
            else:
                os.environ["FONTCONFIG_FILE"] = previous
    return output


def svg_to_png(
    svg_path: Path, png_path: Path | None = None, scale: float = 1.5
) -> Path:
    """Rasterize an SVG file to PNG for visual checking and return the PNG path.

    The default `png_path` sits next to the SVG with the `.drawio.svg` (or
    `.svg`) suffix replaced by `.png`. `scale` multiplies the SVG's own size.

    Raises:
        FileNotFoundError: if `svg_path` does not exist.
        ValueError: if `scale` is not positive.
    """
    if scale <= 0:
        raise ValueError(f"scale must be positive, got {scale}")
    if not svg_path.is_file():
        raise FileNotFoundError(f"SVG not found: {svg_path}")
    if png_path is None:
        stem = svg_path.name.removesuffix(".svg").removesuffix(".drawio")
        png_path = svg_path.with_name(f"{stem}.png")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    import cairosvg  # pyright: ignore[reportMissingTypeStubs]

    cast(Any, cairosvg).svg2png(url=str(svg_path), write_to=str(png_path), scale=scale)
    return png_path
