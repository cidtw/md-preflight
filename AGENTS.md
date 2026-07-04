# Project Agent Instructions
## Project Summary
Deterministic promotion preflight checker that validates Excel/CSV inputs with a rule engine and produces a report and checklist.
## Stack
FastAPI, Pandas, Pydantic, openpyxl, Python 3.11+, ruff, basedpyright, pytest.
## Important Directories
- `app`: API, ingest, rules, and services
- `tests`: rule and API coverage
- `docs`: design notes
- `handoff`: project work history
- `outputs`: generated reports
## Before Editing
- Check `git status`.
- Read `README.md` and relevant docs.
- Do not rename core directories without explicit instruction.
- Do not change API contracts without updating docs.
## Validation
- `uv run ruff check app tests`
- `uv run basedpyright app tests`
- `uv run pytest`
## Handoff Rule
After meaningful changes, write a handoff note in:
`handoff/YYYY-MM-DD-summary.md`
