"""Markdown to print-ready HTML (the input for the PDF renderer)."""

import html
import itertools

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token

DEFAULT_CSS = """
@page {
  size: A4;
  margin: 16mm 14mm 18mm 14mm;
  @bottom-left { font-family: Arial, sans-serif; font-size: 8pt; color: #777; }
  @bottom-right { content: "page " counter(page) " of " counter(pages);
                  font-family: Arial, sans-serif; font-size: 8pt; color: #777; }
}
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.4;
       color: #1f2328; }
h1 { font-size: 20pt; margin: 0 0 6pt; border-bottom: 2px solid #d0d7de;
     padding-bottom: 4pt; }
h2 { font-size: 14pt; margin: 16pt 0 6pt; border-bottom: 1px solid #d0d7de;
     padding-bottom: 2pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
code { font-family: "DejaVu Sans Mono", Consolas, monospace; font-size: 8.5pt;
       background: #f3f4f6; padding: 0 2px; border-radius: 3px; }
pre { background: #f6f8fa; padding: 6pt 8pt; border-radius: 4px; font-size: 8.5pt;
      white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; }
a { color: #0969da; text-decoration: none; }
hr { border: none; border-top: 1px solid #d0d7de; margin: 10pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.5pt;
        break-inside: auto; }
th, td { border: 1px solid #d0d7de; padding: 3pt 5pt; vertical-align: top;
         text-align: left; }
th { background: #f6f8fa; }
tr { break-inside: avoid; }
figure { margin: 8pt 0 12pt; text-align: center; break-inside: avoid; }
figure img { width: 100%; height: auto; max-height: 245mm; object-fit: contain; }
figcaption { font-size: 8.5pt; color: #57606a; margin-top: 3pt; }
"""


def title_from_markdown(markdown_text: str) -> str | None:
    """Return the text of the document's first level-1 heading, or None.

    Both ATX (`# Title`) and setext (`Title` over `===`) headings count;
    inline formatting is dropped (`# The *API*` gives "The API"). Headings
    inside code blocks do not count.
    """
    tokens = _parser().parse(markdown_text)
    for opening, inline in itertools.pairwise(tokens):
        if opening.type == "heading_open" and opening.tag == "h1":
            text = "".join(
                " " if child.type in ("softbreak", "hardbreak") else child.content
                for child in inline.children or []
                if child.type in ("text", "code_inline", "softbreak", "hardbreak")
            ).strip()
            return text or None
    return None


def markdown_to_html(
    markdown_text: str,
    *,
    title: str,
    extra_css: str = "",
    caption_prefix: str = "Figure: ",
) -> str:
    """Return a complete, print-styled HTML document for `markdown_text`.

    - Markdown is read as CommonMark plus GitHub-style tables, so the result
      matches how GitHub renders the file. Raw HTML in the Markdown is kept.
    - `title` becomes the document `<title>` and the left page footer, shown
      literally (quotes, `<`, `&` are safe). The right footer shows
      "page N of M".
    - An image that is alone in its paragraph becomes a `<figure>` whose
      `<figcaption>` is `caption_prefix` + the image's alt text. Images inside
      running text stay inline, without a caption.
    - `extra_css` is applied after the default style, so it can override it.

    Implementation notes:
        markdown-it-py ("commonmark" preset + "table"). Figures are built on
        the token stream, not by regex over the output. Page footers use
        WeasyPrint's CSS paged-media support; browsers ignore them.
    """
    md = _parser()
    tokens = _figures(md, md.parse(markdown_text), caption_prefix)
    body = md.renderer.render(tokens, md.options, {})
    footer = f"@page {{ @bottom-left {{ content: {_css_string(title)}; }} }}"
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title>"
        f"<style>{DEFAULT_CSS}{footer}\n{extra_css}</style></head>"
        f"<body>{body}</body></html>"
    )


def _parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"xhtmlOut": False}).enable("table")


def _figures(md: MarkdownIt, tokens: list[Token], caption_prefix: str) -> list[Token]:
    """Replace each paragraph that holds only an image with a figure block."""
    out: list[Token] = []
    i = 0
    while i < len(tokens):
        window = tokens[i : i + 3]
        if (
            [t.type for t in window] == ["paragraph_open", "inline", "paragraph_close"]
            and not window[0].hidden
            and len(children := window[1].children or []) == 1
            and children[0].type == "image"
        ):
            renderer = md.renderer
            assert isinstance(renderer, RendererHTML)
            img = renderer.renderInline(children, md.options, {})
            caption = html.escape(caption_prefix + children[0].content, quote=False)
            figure = f"<figure>{img}<figcaption>{caption}</figcaption></figure>\n"
            out.append(Token("html_block", "", 0, content=figure, block=True))
            i += 3
        else:
            out.append(tokens[i])
            i += 1
    return out


def _css_string(text: str) -> str:
    """Quote `text` as a CSS string that is also safe inside a <style> element."""
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("<", "\\3c ")
        .replace("\n", "\\a ")
    )
    return f'"{escaped}"'
