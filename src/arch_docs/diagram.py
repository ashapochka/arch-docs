"""Build a diagram once, render it as an editable .drawio.svg.

A `Diagram` collects shapes and connectors and renders one SVG document with
two views of the same geometry: the SVG drawing (shown by GitHub, editors and
PDF renderers) and the draw.io model in the root's `content` attribute (opened
by draw.io for editing). Connectors use fixed ports and explicit waypoints, so
both views draw the same lines.
"""

import html
import re
from collections.abc import Sequence
from typing import Literal
from xml.sax.saxutils import escape, quoteattr

from arch_docs.geometry import Point, Shape, Side, point_along

FONT = "Helvetica, Arial, sans-serif"
FONT_SIZE = 12
LINE_HEIGHT = 15

type Kind = Literal["ui", "app", "int", "srv", "store", "ext", "plain", "note", "err"]
type EdgeKind = Literal["flow", "dep", "assoc", "inherit", "return"]
type MessageKind = Literal["flow", "return"]
type Align = Literal["center", "left", "right"]

# kind -> (fill, stroke); draw.io's default colour pairs.
PALETTE: dict[Kind, tuple[str, str]] = {
    "ui": ("#dae8fc", "#6c8ebf"),
    "app": ("#d5e8d4", "#82b366"),
    "int": ("#fff2cc", "#d6b656"),
    "srv": ("#ffe6cc", "#d79b00"),
    "store": ("#e1d5e7", "#9673a6"),
    "ext": ("#f5f5f5", "#666666"),
    "plain": ("#ffffff", "#333333"),
    "note": ("#fff9c4", "#d6b656"),
    "err": ("#f8cecc", "#b85450"),
}

# edge kind -> (draw.io end style, dashed, svg marker id or None)
_EDGE_STYLES: dict[EdgeKind, tuple[str, bool, str | None]] = {
    "flow": ("endArrow=block;endFill=1;", False, "block"),
    "dep": ("endArrow=open;endFill=0;dashed=1;", True, "open"),
    "assoc": ("endArrow=none;", False, None),
    "inherit": ("endArrow=block;endFill=0;dashed=1;endSize=10;", True, "tri"),
    "return": ("endArrow=open;endFill=0;dashed=1;", True, "open"),
}

_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _esc_html(text: str) -> str:
    return html.escape(text, quote=False)


def _label_html(lines: list[str], bold_first: bool) -> str:
    parts = [_esc_html(line) for line in lines]
    if bold_first and parts:
        parts[0] = f"<b>{parts[0]}</b>"
    return "<br>".join(parts)


class Diagram:
    """An editable diagram of `width` x `height` pixels, saved as `<name>.drawio.svg`.

    Shapes are placed with absolute coordinates and addressed by a key that
    connectors refer to. Labels split into lines on `\\n`. Rendering is
    deterministic: the same calls produce the same output.

    Raises:
        ValueError: if `name` is not a safe file stem (letters, digits, `.`,
            `_`, `-`; starting with a letter or digit), or a size is not positive.
    """

    def __init__(self, name: str, width: int, height: int) -> None:
        if not _NAME_RE.fullmatch(name):
            raise ValueError(f"invalid diagram name {name!r}: use letters, digits, ._-")
        if width <= 0 or height <= 0:
            raise ValueError(f"diagram size must be positive, got {width}x{height}")
        self.name: str = name
        self.width: int = width
        self.height: int = height
        self.shapes: dict[str, Shape] = {}
        self._cells: list[str] = []
        self._back: list[str] = []  # SVG drawn first (containers, frames)
        self._svg: list[str] = []
        self._front: list[str] = []  # SVG drawn last (labels)
        self._n: int = 0

    # ------------------------------------------------------------- helpers
    def _register(self, key: str, x: float, y: float, w: float, h: float) -> Shape:
        """Record a shape under `key` and return it.

        Raises:
            ValueError: if `key` is empty, starts with `_` (reserved for
                generated ids), or is already used in this diagram.
        """
        if not key or key.startswith("_"):
            raise ValueError(
                f"shape key {key!r} must be non-empty and not start with '_'"
            )
        if key in self.shapes:
            raise ValueError(f"shape key {key!r} is already used in {self.name!r}")
        shape = Shape(key, x, y, w, h)
        self.shapes[key] = shape
        return shape

    def _shape(self, key: str) -> Shape:
        try:
            return self.shapes[key]
        except KeyError:
            raise KeyError(
                f"no shape with key {key!r} in diagram {self.name!r}"
            ) from None

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"_{prefix}{self._n}"

    def _text(
        self,
        out: list[str],
        lines: list[str],
        cx: float,
        cy: float,
        *,
        bold_first: bool = False,
        anchor: str = "middle",
        size: int = FONT_SIZE,
        color: str = "#000000",
        italic: bool = False,
        valign: Literal["middle", "top"] = "middle",
    ) -> None:
        if valign == "middle":
            y0 = cy - (len(lines) - 1) * LINE_HEIGHT / 2 + size * 0.35
        else:  # cy is the top edge
            y0 = cy + size
        style = ' font-style="italic"' if italic else ""
        for i, line in enumerate(lines):
            weight = "bold" if (bold_first and i == 0) else "normal"
            out.append(
                f'<text x="{cx:.1f}" y="{y0 + i * LINE_HEIGHT:.1f}" font-family="{FONT}" '
                f'font-size="{size}" font-weight="{weight}" fill="{color}" '
                f'text-anchor="{anchor}"{style}>{escape(line)}</text>'
            )

    def _vertex(
        self, cid: str, value: str, style: str, x: float, y: float, w: float, h: float
    ) -> None:
        self._cells.append(
            f'<mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" '
            f'height="{h}" as="geometry"/></mxCell>'
        )

    def _stick(self, x: float, y: float, w: float, h: float) -> None:
        cx = x + w / 2
        hr = h / 8
        self._svg.append(
            f'<g fill="none" stroke="#333333" stroke-width="1.4">'
            f'<circle cx="{cx}" cy="{y + hr}" r="{hr}" fill="#ffffff"/>'
            f'<line x1="{cx}" y1="{y + 2 * hr}" x2="{cx}" y2="{y + h * 0.62}"/>'
            f'<line x1="{x}" y1="{y + h * 0.36}" x2="{x + w}" y2="{y + h * 0.36}"/>'
            f'<line x1="{cx}" y1="{y + h * 0.62}" x2="{x}" y2="{y + h}"/>'
            f'<line x1="{cx}" y1="{y + h * 0.62}" x2="{x + w}" y2="{y + h}"/></g>'
        )

    # -------------------------------------------------------------- shapes
    def box(
        self,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        kind: Kind = "app",
        *,
        bold_first: bool = True,
        rounded: bool = True,
        size: int = FONT_SIZE,
        dashed: bool = False,
    ) -> Shape:
        """Add a (rounded) rectangle; the first label line is bold by default."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        lines = label.split("\n")
        style = (
            f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};fontSize={size};fontFamily=Helvetica;"
            + ("arcSize=12;" if rounded else "")
            + ("dashed=1;" if dashed else "")
        )
        self._vertex(key, _label_html(lines, bold_first), style, x, y, w, h)
        rx = 6 if rounded else 0
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self._svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1"{dash}/>'
        )
        self._text(
            self._svg, lines, x + w / 2, y + h / 2, bold_first=bold_first, size=size
        )
        return shape

    def container(
        self,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        kind: Kind = "ext",
        *,
        dashed: bool = True,
        size: int = 13,
    ) -> Shape:
        """Add a titled group frame, drawn behind every other shape."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        style = (
            "rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;align=left;"
            f"spacingLeft=8;spacingTop=2;fontStyle=1;fontSize={size};"
            f"fillColor={fill};strokeColor={stroke};fontFamily=Helvetica;"
            + ("dashed=1;" if dashed else "")
        )
        self._vertex(key, _esc_html(title), style, x, y, w, h)
        dash = ' stroke-dasharray="8 4"' if dashed else ""
        self._back.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'fill-opacity="0.55" stroke="{stroke}" stroke-width="1.2"{dash}/>'
        )
        self._text(
            self._back, [title], x + 10, y + 2,
            anchor="start", valign="top", size=size, bold_first=True,
        )  # fmt: skip
        return shape

    def cylinder(
        self, key: str, x: float, y: float, w: float, h: float, label: str,
        kind: Kind = "store",
    ) -> Shape:  # fmt: skip
        """Add a database/storage cylinder."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        lines = label.split("\n")
        style = (
            "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;"
            f"size=8;fillColor={fill};strokeColor={stroke};fontSize={FONT_SIZE};"
            "fontFamily=Helvetica;"
        )
        self._vertex(key, _label_html(lines, True), style, x, y, w, h)
        r = 8
        self._svg.append(
            f'<path d="M{x},{y + r} a{w / 2},{r} 0 0,0 {w},0 a{w / 2},{r} 0 0,0 {-w},0 '
            f'v{h - 2 * r} a{w / 2},{r} 0 0,0 {w},0 v{-(h - 2 * r)}" fill="{fill}" '
            f'stroke="{stroke}"/>'
        )
        self._text(self._svg, lines, x + w / 2, y + h / 2 + 4, bold_first=True)
        return shape

    def note(
        self, key: str, x: float, y: float, w: float, h: float, label: str,
        *, size: int = 11,
    ) -> Shape:  # fmt: skip
        """Add a dog-eared note with left-aligned text."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE["note"]
        lines = label.split("\n")
        style = (
            "shape=note;whiteSpace=wrap;html=1;size=12;align=left;spacingLeft=6;"
            f"fillColor={fill};strokeColor={stroke};fontSize={size};fontFamily=Helvetica;"
        )
        self._vertex(key, _label_html(lines, False), style, x, y, w, h)
        c = 12
        self._svg.append(
            f'<path d="M{x},{y} h{w - c} l{c},{c} v{h - c} h{-w} z M{x + w - c},{y} '
            f'v{c} h{c}" fill="{fill}" stroke="{stroke}"/>'
        )
        self._text(self._svg, lines, x + 7, y + h / 2, anchor="start", size=size)
        return shape

    def ellipse(
        self, key: str, x: float, y: float, w: float, h: float, label: str,
        kind: Kind = "ui",
    ) -> Shape:  # fmt: skip
        """Add an ellipse (a use case)."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        lines = label.split("\n")
        style = (
            f"ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"fontSize={FONT_SIZE};fontFamily=Helvetica;"
        )
        self._vertex(key, _label_html(lines, False), style, x, y, w, h)
        self._svg.append(
            f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" '
            f'fill="{fill}" stroke="{stroke}"/>'
        )
        self._text(self._svg, lines, x + w / 2, y + h / 2)
        return shape

    def diamond(
        self, key: str, x: float, y: float, w: float, h: float, label: str,
        kind: Kind = "int",
    ) -> Shape:  # fmt: skip
        """Add a decision diamond (activity diagrams)."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        lines = label.split("\n")
        style = (
            f"rhombus;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"fontSize={FONT_SIZE};fontFamily=Helvetica;"
        )
        self._vertex(key, _label_html(lines, False), style, x, y, w, h)
        self._svg.append(
            f'<polygon points="{x + w / 2},{y} {x + w},{y + h / 2} {x + w / 2},{y + h} '
            f'{x},{y + h / 2}" fill="{fill}" stroke="{stroke}"/>'
        )
        self._text(self._svg, lines, x + w / 2, y + h / 2)
        return shape

    def terminal(
        self, key: str, x: float, y: float, w: float, h: float, label: str,
        kind: Kind = "plain",
    ) -> Shape:  # fmt: skip
        """Add a start/end pill (activity diagrams)."""
        shape = self._register(key, x, y, w, h)
        fill, stroke = PALETTE[kind]
        style = (
            f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};fontSize={FONT_SIZE};fontFamily=Helvetica;fontStyle=1;"
        )
        self._vertex(key, _esc_html(label), style, x, y, w, h)
        self._svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.4"/>'
        )
        self._text(self._svg, [label], x + w / 2, y + h / 2, bold_first=True)
        return shape

    def actor(
        self, key: str, x: float, y: float, label: str, w: float = 30, h: float = 60
    ) -> Shape:
        """Add a UML stick-figure actor with its label below."""
        shape = self._register(key, x, y, w, h)
        lines = label.split("\n")
        style = (
            "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
            f"outlineConnect=0;fontSize={FONT_SIZE};fontFamily=Helvetica;fontStyle=1;"
        )
        self._vertex(key, _label_html(lines, False), style, x, y, w, h)
        self._stick(x, y, w, h)
        self._text(
            self._svg, lines, x + w / 2, y + h + 2, valign="top", bold_first=True
        )
        return shape

    def classbox(
        self,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float | None,
        name: str,
        body: Sequence[str],
        kind: Kind = "store",
        *,
        stereotype: str | None = None,
    ) -> Shape:
        """Add a UML class box: optional «stereotype», bold name, member lines.

        `h=None` sizes the box to its content. Leading double spaces in body
        lines are kept as indentation.
        """
        fill, stroke = PALETTE[kind]
        members = [b.replace("  ", "  ") for b in body]
        head = ([f"«{stereotype}»"] if stereotype else []) + [name]
        if h is None:
            h = 4 + len(head) * 14 + 5 + len(members) * 14 + 8
        shape = self._register(key, x, y, w, h)
        head_html = "<br>".join(
            (
                f"<i>{_esc_html(t)}</i>"
                if t.startswith("«")
                else f"<b>{_esc_html(t)}</b>"
            )
            for t in head
        )
        body_html = "<br>".join(_esc_html(b) for b in members)
        value = (
            f'<p style="margin:0px;margin-top:4px;text-align:center;">{head_html}</p>'
            '<hr size="1" style="border-style:solid;">'
            f'<p style="margin:0px;margin-left:6px;">{body_html}</p>'
        )
        style = (
            "verticalAlign=top;align=left;overflow=fill;html=1;whiteSpace=wrap;"
            f"fillColor={fill};strokeColor={stroke};fontSize=11;fontFamily=Helvetica;"
        )
        self._vertex(key, value, style, x, y, w, h)
        self._svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{stroke}"/>'
        )
        ty = y + 4
        for t in head:
            italic = t.startswith("«")
            weight = "normal" if italic else "bold"
            style_attr = ' font-style="italic"' if italic else ""
            self._svg.append(
                f'<text x="{x + w / 2}" y="{ty + 12}" font-family="{FONT}" font-size="11" '
                f'font-weight="{weight}" text-anchor="middle"{style_attr}>'
                f"{escape(t)}</text>"
            )
            ty += 14
        sep = ty + 5
        self._svg.append(
            f'<line x1="{x}" y1="{sep}" x2="{x + w}" y2="{sep}" stroke="{stroke}"/>'
        )
        for i, b in enumerate(members):
            self._svg.append(
                f'<text x="{x + 6}" y="{sep + 15 + i * 14}" font-family="{FONT}" '
                f'font-size="11" text-anchor="start">{escape(b)}</text>'
            )
        return shape

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        *,
        size: int = 11,
        align: Align = "center",
        italic: bool = False,
        color: str = "#333333",
        bold: bool = False,
    ) -> None:
        """Add free text (not connectable), drawn above all shapes."""
        lines = label.split("\n")
        font_style = (2 if italic else 0) | (1 if bold else 0)
        style = (
            f"text;html=1;align={align};verticalAlign=middle;whiteSpace=wrap;"
            f"fontSize={size};fontFamily=Helvetica;fontColor={color};"
            + (f"fontStyle={font_style};" if font_style else "")
        )
        self._vertex(self._id("t"), _label_html(lines, False), style, x, y, w, h)
        anchor = {"center": "middle", "left": "start", "right": "end"}[align]
        cx = {"center": x + w / 2, "left": x + 2, "right": x + w - 2}[align]
        n = len(lines)
        y0 = y + h / 2 - (n - 1) * LINE_HEIGHT / 2 + size * 0.35
        extra = (' font-style="italic"' if italic else "") + (
            ' font-weight="bold"' if bold else ""
        )
        for i, line in enumerate(lines):
            self._front.append(
                f'<text x="{cx}" y="{y0 + i * LINE_HEIGHT:.1f}" font-family="{FONT}" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{color}"{extra}>'
                f"{escape(line)}</text>"
            )

    # --------------------------------------------------------------- edges
    def edge(
        self,
        src: str,
        s_side: Side,
        dst: str,
        d_side: Side,
        label: str = "",
        kind: EdgeKind = "flow",
        *,
        via: Sequence[Point] = (),
        s_f: float = 0.5,
        d_f: float = 0.5,
        label_pos: float = 0.5,
        label_dy: float = 0.0,
        color: str = "#333333",
    ) -> None:
        """Connect two shapes from a port on `s_side` to a port on `d_side`.

        `via` lists waypoints in order; `s_f`/`d_f` place the ports along their
        sides (0..1). `label_pos` (0..1) places the label along the line.
        Kinds: flow (solid, filled arrow), dep (dashed, open arrow), assoc
        (solid, no arrow), inherit (dashed, hollow triangle), return (dashed,
        open arrow).

        Raises:
            KeyError: if `src` or `dst` is not a shape key in this diagram.
        """
        a = self._shape(src).port(s_side, s_f)
        b = self._shape(dst).port(d_side, d_f)
        pts: list[Point] = [(a.x, a.y), *via, (b.x, b.y)]
        end, dashed, marker = _EDGE_STYLES[kind]
        style = (
            f"html=1;rounded=0;{end}exitX={a.fx};exitY={a.fy};exitDx=0;exitDy=0;"
            f"entryX={b.fx};entryY={b.fy};entryDx=0;entryDy=0;fontSize=11;"
            f"fontFamily=Helvetica;labelBackgroundColor=#ffffff;strokeColor={color};"
        )
        pts_xml = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in via)
        # draw.io places edge labels at x in -1..1 along the edge.
        geo_attrs = f'x="{(label_pos - 0.5) * 2:.3f}" y="{label_dy}" ' if label else ""
        geo = (
            f'<mxGeometry {geo_attrs}relative="1" as="geometry">'
            + (f'<Array as="points">{pts_xml}</Array>' if via else "")
            + "</mxGeometry>"
        )
        self._cells.append(
            f'<mxCell id="{self._id("e")}" value={quoteattr(_esc_html(label))} '
            f'style={quoteattr(style)} edge="1" parent="1" source="{src}" '
            f'target="{dst}">{geo}</mxCell>'
        )
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        mk = f' marker-end="url(#{marker})"' if marker else ""
        self._svg.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.3"{dash}{mk}/>'
        )
        if label:
            lx, ly = point_along(pts, label_pos)
            self._edge_label(label, lx, ly + label_dy)

    def _edge_label(self, label: str, lx: float, ly: float) -> None:
        lines = label.split("\n")
        wmax = max(len(t) for t in lines) * 6.1 + 6
        hh = len(lines) * LINE_HEIGHT
        self._front.append(
            f'<rect x="{lx - wmax / 2:.1f}" y="{ly - hh / 2:.1f}" width="{wmax:.1f}" '
            f'height="{hh}" fill="#ffffff"/>'
        )
        self._text(self._front, lines, lx, ly, size=11, color="#333333")

    # ------------------------------------------------------- sequence parts
    def lifeline(
        self,
        key: str,
        cx: float,
        top: float,
        bottom: float,
        label: str,
        kind: Kind = "app",
        *,
        w: float | None = None,
        actor: bool = False,
    ) -> Shape:
        """Add a sequence-diagram participant centred at `cx`, from `top` to `bottom`.

        The default width fits the label (at least 110). `actor=True` draws a
        stick figure head instead of a box.
        """
        lines = label.split("\n")
        width = w or max(110, max(len(t) for t in lines) * 7 + 20)
        x = cx - width / 2
        shape = self._register(key, x, top, width, bottom - top)
        head = 50 if actor else 40
        fill, stroke = PALETTE[kind]
        style = (
            "shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;"
            "container=0;collapsible=0;recursiveResize=0;outlineConnect=0;"
            f"size={head};fillColor={fill};strokeColor={stroke};fontSize={FONT_SIZE};"
            "fontFamily=Helvetica;fontStyle=1;"
            + ("participant=umlActor;verticalLabelPosition=top;" if actor else "")
        )
        self._vertex(key, _label_html(lines, False), style, x, top, width, bottom - top)
        self._svg.append(
            f'<line x1="{cx}" y1="{top + head}" x2="{cx}" y2="{bottom}" '
            f'stroke="{stroke}" stroke-dasharray="5 4"/>'
        )
        if actor:
            self._stick(cx - 11, top + 4, 22, head - 16)
            self._text(
                self._svg, lines, cx, top - 4 - (len(lines) - 1) * LINE_HEIGHT / 2,
                bold_first=True,
            )  # fmt: skip
        else:
            self._svg.append(
                f'<rect x="{x}" y="{top}" width="{width}" height="{head}" fill="{fill}" '
                f'stroke="{stroke}"/>'
            )
            n = len(lines)
            y0 = top + head / 2 - (n - 1) * LINE_HEIGHT / 2 + FONT_SIZE * 0.35
            for i, line in enumerate(lines):
                self._svg.append(
                    f'<text x="{cx}" y="{y0 + i * LINE_HEIGHT:.1f}" font-family="{FONT}" '
                    f'font-size="{FONT_SIZE}" font-weight="bold" text-anchor="middle">'
                    f"{escape(line)}</text>"
                )
        return shape

    def msg(
        self, src: str, dst: str, y: float, label: str, kind: MessageKind = "flow"
    ) -> None:
        """Add a horizontal message between two lifelines at height `y`.

        Raises:
            KeyError: if `src` or `dst` is not a shape key in this diagram.
        """
        x1 = self._shape(src).cx
        x2 = self._shape(dst).cx
        end, dashed, marker = _EDGE_STYLES[kind]
        style = (
            f"html=1;verticalAlign=bottom;{end}fontSize=11;fontFamily=Helvetica;"
            "labelBackgroundColor=none;"
        )
        self._cells.append(
            f'<mxCell id="{self._id("m")}" value={quoteattr(_esc_html(label))} '
            f'style={quoteattr(style)} edge="1" parent="1"><mxGeometry relative="1" '
            f'as="geometry"><mxPoint x="{x1}" y="{y}" as="sourcePoint"/><mxPoint '
            f'x="{x2}" y="{y}" as="targetPoint"/></mxGeometry></mxCell>'
        )
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self._svg.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#333333" '
            f'stroke-width="1.2"{dash} marker-end="url(#{marker})"/>'
        )
        self._text(self._front, [label], (x1 + x2) / 2, y - 8, size=11)

    def self_msg(self, who: str, y: float, label: str, h: float = 22) -> None:
        """Add a message from a lifeline to itself, starting at `y`, `h` tall.

        Raises:
            KeyError: if `who` is not a shape key in this diagram.
        """
        x = self._shape(who).cx
        style = "html=1;endArrow=block;endFill=1;rounded=0;fontSize=11;"
        self._cells.append(
            f'<mxCell id="{self._id("m")}" value="" style={quoteattr(style)} edge="1" '
            f'parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x}" '
            f'y="{y}" as="sourcePoint"/><mxPoint x="{x}" y="{y + h}" as="targetPoint"/>'
            f'<Array as="points"><mxPoint x="{x + 30}" y="{y}"/><mxPoint x="{x + 30}" '
            f'y="{y + h}"/></Array></mxGeometry></mxCell>'
        )
        self._svg.append(
            f'<path d="M{x},{y} L{x + 30},{y} L{x + 30},{y + h} L{x},{y + h}" '
            f'fill="none" stroke="#333333" stroke-width="1.2" marker-end="url(#block)"/>'
        )
        self.text(x + 36, y - 2, 240, h + 4, label, align="left")

    def frame(
        self, x: float, y: float, w: float, h: float, tag: str, cond: str = ""
    ) -> None:
        """Add a combined fragment (`alt`, `loop`, `opt`...) with an optional guard."""
        style = (
            "shape=umlFrame;whiteSpace=wrap;html=1;width=56;height=20;fontSize=11;"
            "fontStyle=1;fontFamily=Helvetica;fillColor=none;strokeColor=#666666;"
        )
        self._vertex(self._id("f"), _esc_html(tag), style, x, y, w, h)
        self._back.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
            f'stroke="#666666"/><path d="M{x},{y + 20} h48 l8,-8 v-12" fill="#f5f5f5" '
            f'stroke="#666666"/>'
        )
        self._text(self._back, [tag], x + 26, y + 10, size=11, bold_first=True)
        if cond:
            self.text(x + 62, y + 1, w - 70, 18, cond, align="left", italic=True)

    def divider(self, x: float, y: float, w: float, cond: str) -> None:
        """Add a dashed operand separator inside a frame, with its guard."""
        self._cells.append(
            f'<mxCell id="{self._id("d")}" value="" style="endArrow=none;dashed=1;'
            f'html=1;strokeColor=#666666;" edge="1" parent="1"><mxGeometry relative="1" '
            f'as="geometry"><mxPoint x="{x}" y="{y}" as="sourcePoint"/><mxPoint '
            f'x="{x + w}" y="{y}" as="targetPoint"/></mxGeometry></mxCell>'
        )
        self._back.append(
            f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="#666666" '
            f'stroke-dasharray="6 4"/>'
        )
        self.text(x + 8, y + 1, w - 16, 18, cond, align="left", italic=True)

    # ---------------------------------------------------------------- output
    @staticmethod
    def _arrow_defs() -> str:
        # stroke-dasharray="none": markers otherwise inherit a dashed line's dashes.
        return (
            "<defs>"
            '<marker id="block" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" '
            'markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#333333"/></marker>'
            '<marker id="open" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" '
            'markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10" '
            'fill="none" stroke="#333333" stroke-width="1.4" '
            'stroke-dasharray="none"/></marker>'
            '<marker id="tri" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="15" '
            'markerHeight="15" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            'fill="#ffffff" stroke="#333333" stroke-width="1" '
            'stroke-dasharray="none"/></marker>'
            "</defs>"
        )

    def render(self) -> str:
        """Return the .drawio.svg document: SVG drawing plus embedded draw.io model.

        Every shape key is a cell id in the model; generated ids start with `_`.
        """
        model = (
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="1" gridSize="10" '
            'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" '
            f'pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
            'math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(self._cells)
            + "</root></mxGraphModel>"
        )
        mxfile = (
            '<mxfile host="Electron" agent="arch-docs" version="24.7.17">'
            f'<diagram id="{self.name}" name="{self.name}">{model}</diagram></mxfile>'
        )
        body = "".join(self._back + self._svg + self._front)
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
            f'width="{self.width}px" height="{self.height}px" '
            f'viewBox="-0.5 -0.5 {self.width} {self.height}" content={quoteattr(mxfile)}>'
            + self._arrow_defs()
            + f'<rect x="-0.5" y="-0.5" width="{self.width}" height="{self.height}" '
            'fill="#ffffff"/>' + body + "</svg>\n"
        )
