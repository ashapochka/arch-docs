import re

import pytest

from arch_docs.html import DEFAULT_CSS, markdown_to_html, title_from_markdown


def body(html: str) -> str:
    match = re.search(r"<body>(.*)</body>", html, re.DOTALL)
    assert match
    return match.group(1)


def test_is_complete_document_with_title():
    out = markdown_to_html("hi", title="My Doc")
    assert out.startswith("<!doctype html>")
    assert "<title>My Doc</title>" in out
    assert '<meta charset="utf-8">' in out


def test_title_is_shown_literally_in_title_and_footer():
    out = markdown_to_html("x", title='A "q" <b> & \\ c')
    assert "<title>A &quot;q&quot; &lt;b&gt; &amp; \\ c</title>" in out
    # CSS string: quotes and backslashes escaped; "<" escaped for the <style> block.
    assert r'content: "A \"q\" \3c b> & \\ c"' in out


def test_footer_shows_page_numbers():
    out = markdown_to_html("x", title="t")
    assert 'counter(page) " of " counter(pages)' in out


def test_renders_github_style_tables():
    out = body(markdown_to_html("| a | b |\n|---|---|\n| 1 | 2 |\n", title="t"))
    assert "<table>" in out and "<td>1</td>" in out


def test_follows_commonmark_lists():
    # python-markdown merges this into one paragraph; CommonMark makes a list.
    out = body(markdown_to_html("Intro:\n- one\n- two\n", title="t"))
    assert "<ul>" in out and "<li>one</li>" in out


def test_keeps_raw_html():
    out = body(markdown_to_html("<div class='x'>raw</div>\n", title="t"))
    assert "<div class='x'>raw</div>" in out


def test_standalone_image_becomes_captioned_figure():
    out = body(markdown_to_html("![Runtime view](d/rt.drawio.svg)\n", title="t"))
    assert out.strip() == (
        '<figure><img src="d/rt.drawio.svg" alt="Runtime view">'
        "<figcaption>Figure: Runtime view</figcaption></figure>"
    )


def test_caption_prefix_is_configurable_and_alt_is_escaped():
    out = body(markdown_to_html("![a < b](x.svg)\n", title="t", caption_prefix=""))
    assert "<figcaption>a &lt; b</figcaption>" in out


def test_inline_image_stays_inline_without_caption():
    out = body(markdown_to_html("See ![icon](i.svg) here.\n", title="t"))
    assert "<figure>" not in out
    assert '<p>See <img src="i.svg" alt="icon"> here.</p>' in out


def test_extra_css_comes_after_default_css():
    out = markdown_to_html("x", title="t", extra_css="body { color: red; }")
    assert out.index(DEFAULT_CSS) < out.index("body { color: red; }")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Title\n\ntext", "Title"),
        ("intro\n\n# First\n# Second", "First"),
        ("Setext\n======\n", "Setext"),
        ("# The *API* `x`", "The API x"),
        ("## Only h2", None),
        ("```\n# not a heading\n```\n", None),
        ("", None),
    ],
)
def test_title_from_markdown(text, expected):
    assert title_from_markdown(text) == expected
