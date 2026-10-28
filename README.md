# arch-docs

Architecture documentation as code:

- **Diagrams in Python → `.drawio.svg`.** Each file is a normal SVG (shown by GitHub,
  IDE Markdown previews and PDF renderers) *and* an editable draw.io diagram (the model
  is embedded in the SVG). Describe the diagram once; both views share the same geometry.
- **Markdown → PDF** with the diagrams embedded as vectors, GitHub-compatible Markdown
  (CommonMark + tables), captioned figures, page footers and the right fonts.
- **Checks**: validate the embedded draw.io model, and rasterize to PNG to inspect the layout.

It is also a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills):
cloned into `~/.claude/skills/arch-docs`, it teaches Claude when and how to use it
(see [SKILL.md](SKILL.md)).

## Install

```bash
git clone https://github.com/ashapochka/arch-docs ~/.claude/skills/arch-docs
cd ~/.claude/skills/arch-docs && uv sync
```

WeasyPrint and CairoSVG need Pango and Cairo. On Debian/Ubuntu:
`apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2`.

## Use

From any project (paths are relative to the current directory):

```bash
AD=~/.claude/skills/arch-docs
uv run --project $AD python docs/diagrams/build_diagrams.py docs/diagrams
uv run --project $AD arch-docs check docs/diagrams/*.drawio.svg
uv run --project $AD arch-docs preview docs/diagrams/*.drawio.svg --out-dir /tmp/png
uv run --project $AD arch-docs pdf docs/architecture.md     # writes docs/architecture.pdf
```

A diagram script:

```python
from pathlib import Path

from arch_docs import Diagram
from arch_docs.adapters import save_diagram

d = Diagram("runtime-view", 700, 200)
d.actor("user", 30, 70, "User")
d.box("cli", 120, 70, 200, 56, "CLI\nprompt_toolkit UI", "ui")
d.cylinder("db", 470, 68, 200, 60, "Store\nin memory")
d.edge("user", "right", "cli", "left", "types")
d.edge("cli", "right", "db", "left", "reads/writes", kind="dep")
save_diagram(d, Path("docs/diagrams"))
```

[examples/mcp_chat_cli/diagrams.py](examples/mcp_chat_cli/diagrams.py) has a full set:
runtime view, use cases, logical structure (UML classes), module dependencies,
contracts, three sequence diagrams and an activity diagram.

## Subagent: architecture-writer

[agents/architecture-writer.md](agents/architecture-writer.md) is a Claude Code subagent. It recovers a solution's architecture from code and docs and writes an evidence-based analysis report: Markdown with these diagrams, rendered to PDF. The report is structured by Views and Beyond (views), ADD (drivers and significant requirements) and ATAM (sensitivity points, tradeoffs, risks). It preloads the `arch-docs`, `doc-coauthoring` and `pdf` skills.

Install it, and the two Anthropic skills it uses, at user level:

```bash
mkdir -p ~/.claude/agents
ln -s ~/.claude/skills/arch-docs/agents/architecture-writer.md ~/.claude/agents/
# pdf and doc-coauthoring come from https://github.com/anthropics/skills
# (install the plugins, or copy skills/pdf and skills/doc-coauthoring into ~/.claude/skills)
```

Then ask Claude Code: *"use the architecture-writer agent to analyze this project"*. It writes `docs/architecture-analysis.md`, the matching `.pdf` and `docs/diagrams/aa-*.drawio.svg`. It never overwrites an existing architecture doc and doesn't commit.

## Develop

```bash
uv run pytest                     # tests (-m "not slow" skips WeasyPrint/cairo rendering)
uv run ruff check . && uv run ruff format --check .
uv run basedpyright
```

See [CLAUDE.md](CLAUDE.md) for conventions and [docs/decisions.md](docs/decisions.md)
for the decision log.

## License

MIT
