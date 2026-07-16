"""Run Node smoke tests for app/web/wizard_logic.mjs (frontend gating)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_wizard_logic.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_wizard_logic_node_smoke() -> None:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    proc = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"wizard_logic smoke failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "all wizard_logic smoke checks passed" in proc.stdout
