# arch-docs

Toolkit and Claude Code skill: Python-built `.drawio.svg` diagrams, Markdown → PDF, diagram checks. `SKILL.md` is the user-facing skill entry point; keep it in sync with the CLI and the `Diagram` API.

## Commands

```bash
uv run pytest                      # tests; -m "not slow" skips WeasyPrint/cairo rendering
uv run ruff check . && uv run ruff format --check .
uv run basedpyright                # recommended mode; 0 errors, 0 warnings
uv run arch-docs --help            # pdf | preview | check
uv run python examples/mcp_chat_cli/diagrams.py /tmp/out   # regenerate the example set
```

The tree is lint-clean and type-clean: run all three before committing.

## Layout (clean architecture: dependencies point inward)

- Core (pure; builds strings, no I/O):
  - `geometry.py`: `Shape`, ports, `point_along`.
  - `diagram.py`: the `Diagram` builder and `render()`.
  - `model.py`: extract and check the embedded draw.io model.
  - `html.py`: Markdown → print HTML.
  - `fonts.py`: fontconfig XML.
- Edge:
  - `adapters.py`: files, font discovery, WeasyPrint, CairoSVG.
  - `cli.py`: argparse wiring only.
- Core modules never import `adapters`, `cli`, `weasyprint` or `cairosvg`, and never touch files; `adapters` never imports `cli`. `tests/test_architecture.py` enforces this (D-003).
- `examples/`: worked diagram sets. Each has `build() -> list[Diagram]`, validated by `tests/test_examples.py`.
- `docs/decisions.md`: the decision log.

## Decision log

Record important decisions in [docs/decisions.md](docs/decisions.md) when they're made. Read it before changing a contract or the architecture.

- Record decisions that set or change a contract, the architecture, tooling or a convention, or that choose between real alternatives (including the user's choices). Skip routine fixes.
- Entry format: `## D-NNN Title`, then `*date · status*`, **Decision:** (1-3 sentences) and **Why:** (1-2 sentences). No implementation details.
- Never rewrite an entry: add a new one and mark the old one `Superseded by D-NNN`.

## Stubs and docstrings

A stub is the spec: signature plus docstring, with the body `raise NotImplementedError`.

- Summary, Returns and Raises state only what a caller can observe. Library and storage details go under `Implementation notes:`.
- Every contract sentence must be testable and must map to at least one test. Resolve unstated edge cases (empty input, duplicates, escaping, bounds) in the docstring before writing tests.

## Testing (TDD)

Stub → failing tests → implementation.

1. Write the stub with its contract.
2. Write tests in `tests/test_<module>.py` for every contract sentence. Run them and confirm they fail with `NotImplementedError`.
3. Implement until they pass. Never weaken a test to make it pass: if the contract was wrong, fix the docstring first and say so.

- Test the core with plain values and the edge with `tmp_path`. Test the CLI with the adapters monkeypatched (see `FakePdf` in `tests/test_cli.py`).
- Mark tests that run WeasyPrint or CairoSVG `@pytest.mark.slow`.
- Diagram output changes need a visual check: regenerate the example set, run `arch-docs preview` and look at the PNGs. Pixel-compare against the previous output for refactors.
- Record known gaps as `@pytest.mark.xfail(strict=True, reason=...)`.

## Notes

- Python ≥ 3.12 (`type` aliases, PEP 695). Typing: `list[...]`, `X | None`.
- Untyped libraries (weasyprint, cairosvg) are imported lazily in `adapters.py` with a scoped `pyright: ignore[reportMissingTypeStubs]` and used through `Any`.
- The rendered SVG must stay byte-stable for the same input (`render()` is deterministic).
