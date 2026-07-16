# Scripts

## Active

| Script | Purpose |
|--------|---------|
| `verify_wizard_logic.mjs` | Node smoke for multi-session wizard pure logic (precise-address gate, payload sanitize, loading→error restore). Run: `node scripts/verify_wizard_logic.mjs` (also via `pytest tests/test_wizard_logic.py`). |
| `verify_report_export.mjs` | Node smoke for Markdown/CSV report builders. Run: `node scripts/verify_report_export.mjs`. |
| `verify_demo_scenarios.mjs` | Node smoke for third-party demo presets. Run: `node scripts/verify_demo_scenarios.mjs`. |
| `../demo.sh` | End-to-end demo smoke (health · static · evaluate · geo). `./demo.sh` or `./demo.sh --prod`. |

## Archived (v1)

v1 promotion-preflight verify scripts (other than the new ROP `demo.sh`) were removed from the active path.  
Restore older tooling: `git checkout archive/v1-md-preflight -- scripts`
