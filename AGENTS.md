# Project Agent Instructions

## Project Summary

Modular **input → analyze → output** pipeline skeleton (redesign).
Clients submit template parameters; a deterministic weighted engine scores them;
the output stage returns a **one-line recommendation**.

v1 promotion preflight (Excel/CSV rule engine, SPA, Clerk/Neon) is archived:
`archive/v1-md-preflight/` · git tag `archive/v1-md-preflight`.

## Stack

FastAPI, Pydantic, Python 3.11+, ruff, basedpyright, pytest.

## Important Directories

- `app/pipeline`: input / analyze / output stages + runner
- `app/api`: thin HTTP adapter
- `app/web`: minimal placeholder UI
- `docs/redesign`: redesign board and contracts
- `archive/v1-md-preflight`: v1 inventory and restore notes
- `tests`: pipeline and API coverage
- `handoff`: local work history (often gitignored)

## Before Editing

- Check `git status` and current branch (`pivot/project-direction` for redesign).
- Read `docs/redesign/README.md` and `PROJECT_BRIEF.md`.
- Do not restore v1 packages into the active path without an explicit request.
- Do not invent production evaluation weights without research (board R0–R2).
- Do not change API contracts without updating `docs/redesign/pipeline.md`.

## Validation

- `uv run ruff check app tests`
- `uv run basedpyright app`
- `uv run pytest`

## Handoff Rule

After meaningful changes, write a handoff note in:
`handoff/YYYY-MM-DD-summary.md`
