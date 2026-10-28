---
name: arch-docs
description: Write architecture documentation as Markdown with editable draw.io diagrams (.drawio.svg) generated from Python, and render it to PDF. Use when asked for an architecture document, design doc, or UML-style diagrams (use case, sequence, class/logical structure, component, dependency, activity) that should live in a repo, or to turn a Markdown document with SVG images into a PDF.
---

# arch-docs

Toolkit at `~/.claude/skills/arch-docs` (a uv project). Run everything through it
from the target project's directory; paths stay relative to the current directory:

```bash
AD=~/.claude/skills/arch-docs
uv run --project $AD python docs/diagrams/build_diagrams.py docs/diagrams   # generate
uv run --project $AD arch-docs check docs/diagrams/*.drawio.svg              # validate
uv run --project $AD arch-docs preview docs/diagrams/*.drawio.svg --out-dir /tmp/png   # look
uv run --project $AD arch-docs pdf docs/architecture.md                      # PDF next to the md
```

## Workflow

1. **Read the code first.** Every box, arrow and label must match real modules,
   classes and calls. Note the responsibilities, contracts, dependencies and the main
   control/data flows.
2. **Write the diagram script in the target project** (`docs/diagrams/build_diagrams.py`),
   so the diagrams can be regenerated. Copy the structure of
   `$AD/examples/mcp_chat_cli/diagrams.py`: `build() -> list[Diagram]` plus a `main`
   that calls `save_diagram`. It has one worked example per diagram type.
3. **Generate, check and preview.** Run `check`, then `preview` and **look at every
   PNG** (Read the image). Fix overlaps, cut-off labels, arrows crossing boxes and
   labels sitting on lines, then regenerate. Expect two or three rounds.
4. **Write `docs/architecture.md`.** Put each diagram on its own line as
   `![Caption](diagrams/name.drawio.svg)` (it becomes a captioned figure in the PDF)
   with prose that explains it. Don't let the diagram replace the text.
5. **Render the PDF** if asked, then look at a few pages (`pypdf` or rasterize).

## Diagram API (`from arch_docs import Diagram`)

`d = Diagram("name", width, height)`; coordinates are absolute pixels; `\n` splits
label lines; the first line of a box is bold.

| Need | Call |
| --- | --- |
| Component / class box | `box(key, x, y, w, h, label, kind)`; `dashed=True` for optional |
| Group / boundary | `container(key, x, y, w, h, title, kind)` (drawn behind) |
| Data store, file | `cylinder(...)` |
| Annotation | `note(...)` |
| Use case / actor | `ellipse(...)`, `actor(key, x, y, label)` |
| Activity | `terminal(...)` start/end, `diamond(...)` decision, `box` action |
| UML class | `classbox(key, x, y, w, None, name, members, stereotype="Protocol")` |
| Free text | `text(x, y, w, h, label, align="left", italic=True)` |
| Connector | `edge(src, "right", dst, "left", label, kind, via=[(x, y)], s_f=, d_f=, label_pos=)` |
| Sequence | `lifeline(key, cx, top, bottom, label, actor=)`, `msg(a, b, y, label, kind="return")`, `self_msg(a, y, label)`, `frame(x, y, w, h, "alt", "[cond]")`, `divider(x, y, w, "[else]")` |

Kinds (colours): `ui` blue, `app` green, `int` yellow (integration), `srv` orange,
`store` purple, `ext` grey (external), `plain`, `note`, `err` red. Edge kinds: `flow`
(call/data), `dep` (dashed dependency), `assoc`, `inherit` (implements/extends),
`return`.

## Layout rules that avoid rework

- Use a grid: columns about 250 px apart, rows about 90 px; boxes about 200x56.
- Route edges with explicit `via` waypoints. Spread several edges on one side with
  `s_f`/`d_f` (0.25, 0.5, 0.75). Move a label off crossings with `label_pos`.
- Width of text is about 6.1 px per character at size 11 and 7 px at size 12. Size
  boxes from the longest line.
- Sequence diagrams: lifelines about 200 px apart, messages about 30 px apart; widen
  the gap for long labels.
- Keys must be unique and must not start with `_` (reserved for generated ids).

## PDF notes

- `arch-docs pdf SOURCE.md [-o OUT] [--title T] [--css extra.css] [--font-dir DIR | --no-font-dir]`.
  The title defaults to the first `# ` heading.
- The diagrams were laid out with Helvetica/Arial metrics. The tool finds Arial in the
  Windows fonts (on WSL), msttcorefonts or `/Library/Fonts` and maps Helvetica to it.
  Without it, text is wider and can overflow boxes: use `--font-dir`.
- WeasyPrint needs Pango; on Debian/Ubuntu, `apt install libpango-1.0-0 libpangoft2-1.0-0`.

## Improving the toolkit

It is a TDD project. Follow `$AD/CLAUDE.md`, and record decisions in
`$AD/docs/decisions.md`.
