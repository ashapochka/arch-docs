# Decision log

Newest last. Format and rules: see CLAUDE.md.

## D-001 One SVG file holds both the drawing and the draw.io model
*2026-10-28 · accepted*

**Decision:** Diagrams are written as `.drawio.svg`. The SVG body is a static rendering, and the root's `content` attribute carries the uncompressed draw.io model with the same geometry.

**Why:** One file displays in GitHub, IDE previews and PDFs, and still opens in draw.io for editing. There are no PNG exports to keep in sync.

## D-002 Diagrams are generated from Python with explicit geometry
*2026-10-28 · accepted*

**Decision:** Diagrams are described in a Python script using absolute coordinates, fixed connection ports and explicit waypoints, with no auto-layout or routing. The script lives in the documented project and regenerates the files.

**Why:** Both views must draw identical lines, and diagrams must be reviewable and reproducible. Auto-routing in draw.io would diverge from the static SVG.

## D-003 Clean architecture: a pure core, I/O at the edge
*2026-10-28 · accepted*

**Decision:** `geometry`, `diagram`, `model`, `html` and `fonts` only transform values. `adapters` owns the filesystem, WeasyPrint and CairoSVG, and `cli` only wires arguments to them. Fitness tests in `tests/test_architecture.py` enforce the dependency direction.

**Why:** The core is fast to test without fixtures or system libraries. Rendering engines can be swapped without touching diagram or Markdown logic.

## D-004 Markdown is parsed with markdown-it-py (CommonMark + tables)
*2026-10-28 · accepted*

**Decision:** PDF input is parsed with markdown-it-py's `commonmark` preset with tables enabled. Standalone images become captioned figures through a token-stream transform.

**Why:** It renders lists, nesting and tables the way GitHub does. python-markdown merged lists into paragraphs. Working on tokens is robust where regexes over the HTML are not.

## D-005 WeasyPrint renders the PDF, with fonts mapped through fontconfig
*2026-10-28 · accepted*

**Decision:** The PDF comes from WeasyPrint. When an Arial directory is found or given, a temporary fontconfig file adds it and maps Helvetica to Arial.

**Why:** WeasyPrint keeps SVGs as vectors and supports paged media (footers, page counters). The diagrams are laid out for Helvetica/Arial metrics, and wider fallback fonts overflow boxes.

## D-006 One `arch-docs` CLI with `pdf`, `preview` and `check`
*2026-10-28 · accepted*

**Decision:** One console script with three subcommands replaces the per-project `render_pdf.py`. The title, output, CSS and font directory are options with defaults.

**Why:** The same tool serves any project without editing the script. Previewing and checking are steps of the diagram workflow, so they belong in the tool.

## D-007 Shape keys are validated; generated ids are reserved
*2026-10-28 · accepted*

**Decision:** `Diagram` rejects empty or duplicate shape keys and keys starting with `_`, and generated cell ids start with `_`. Diagram names must be safe file stems.

**Why:** The original generator's auto ids (`e1`, `t2`) could collide with user keys, which silently corrupts the draw.io model.

## D-008 The skill directory is the project repository
*2026-10-28 · accepted*

**Decision:** The uv project lives at `~/.claude/skills/arch-docs` and is published as the public GitHub repo `ashapochka/arch-docs`. `SKILL.md` sits at its root.

**Why:** One copy serves as the installed skill and as the development checkout, so improvements take effect immediately and are versioned.

## D-009 Ported code is covered by characterization tests
*2026-10-28 · accepted*

**Decision:** The diagram builder came from working project code. It was ported with behaviour-pinning tests plus a pixel comparison of the regenerated example diagrams, not rewritten test-first. New behaviour follows stub → test → implementation.

**Why:** The existing output was already verified visually. Pinning it guards the port, and strict TDD applies to every change from here on.
