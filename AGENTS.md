# Project Agent Instructions

## Project Summary

Store-specific **Lead Time / Re-Order Point** adjustment service.
Users submit store, trade-area, and product demand parameters; a deterministic
pipeline scores logistics CAPA and demand volatility, matches a knowledge base,
and returns recommended LT/ROP with evidence.

v1 promotion preflight is archived:
`archive/v1-md-preflight/` · git tag `archive/v1-md-preflight`.

## Stack

FastAPI, Pydantic, Python 3.11+, ruff, basedpyright, pytest.

## Important Directories

- `app/pipeline`: input / analyze / output (ROP engine)
- `app/api`: thin HTTP adapter
- `app/web`: form → loading → report UI
- `docs/redesign`: service contracts and board
- `archive/v1-md-preflight`: v1 restore notes
- `tests`: pipeline and API coverage

## Before Editing

- Check `git status` (redesign work on `pivot/project-direction`).
- Read `2026-07-14-New-Service-Flow.md` and `docs/redesign/pipeline.md`.
- Do not hard-code design-doc example narratives into output.
- Prefer size/ticket over store_type when they conflict (emit guidance).
- Extend via pipeline stages; do not restore v1 packages without request.

## Validation

- `uv run ruff check app tests`
- `uv run basedpyright app`
- `uv run pytest`

## Handoff Rule

After meaningful changes, write:
`handoff/YYYY-MM-DD-summary.md`
