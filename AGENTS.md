# Project Agent Instructions

## Status — ARCHIVED (2026-07-22)

This project is **officially closed** and frozen as a **public GitHub archive**.
Do **not** add features, open workstreams, or treat the live demo as supported.
See `ARCHIVE.md` and the banner in `README.md`.

## Project Summary

**Product**: **발주맞춤 · OrderFit** (repo/history may still say `md-preflight`).

Store-specific **Re-Order Point / order-quantity** guide for shop owners and
field operators (not the v1 MD promotion preflight). Users submit store,
trade-area, and product demand parameters; a deterministic pipeline scores
logistics CAPA and demand volatility, matches a knowledge base, and returns
recommended ROP/SS/Q with evidence. LT stays fixed from contract/standard input.

v1 promotion preflight is archived:
`archive/v1-md-preflight/` · git tag `archive/v1-md-preflight`.

Pivot branch at close: `pivot/project-direction`.

**Prod URL (reference only)**: https://baljumatch.vercel.app

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

- **Default: do not edit.** Project is archived (2026-07-22).
- If the user explicitly requests a one-off fix or unarchive: check `git status`,
  read `ARCHIVE.md`, then `docs/redesign/pipeline.md`.
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
