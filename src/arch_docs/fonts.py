"""Font configuration so PDFs use the metrics the diagrams were laid out for."""

from collections.abc import Mapping
from pathlib import Path
from xml.sax.saxutils import escape

DEFAULT_ALIASES: Mapping[str, str] = {"Helvetica": "Arial"}


def fontconfig_xml(
    font_dir: Path,
    cache_dir: Path,
    aliases: Mapping[str, str] = DEFAULT_ALIASES,
) -> str:
    """Return a fontconfig file that adds `font_dir` and maps family aliases.

    The configuration keeps the system's fonts, adds every font in
    `font_dir`, makes each alias key resolve to its value first (by default
    Helvetica → Arial), and caches in `cache_dir`. Paths and family names are
    XML-escaped.
    """
    alias_xml = "".join(
        f'  <alias binding="same"><family>{escape(name)}</family>'
        f"<prefer><family>{escape(target)}</family></prefer></alias>\n"
        for name, target in aliases.items()
    )
    return (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
        "<fontconfig>\n"
        '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
        f"  <dir>{escape(str(font_dir))}</dir>\n"
        f"{alias_xml}"
        f"  <cachedir>{escape(str(cache_dir))}</cachedir>\n"
        "</fontconfig>\n"
    )
