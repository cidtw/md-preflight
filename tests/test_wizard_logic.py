"""Run Node smoke tests for frontend pure modules."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WIZARD_SCRIPT = ROOT / "scripts" / "verify_wizard_logic.mjs"
EXPORT_SCRIPT = ROOT / "scripts" / "verify_report_export.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_wizard_logic_node_smoke() -> None:
    assert WIZARD_SCRIPT.is_file(), f"missing {WIZARD_SCRIPT}"
    proc = subprocess.run(
        ["node", str(WIZARD_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"wizard_logic smoke failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "all wizard_logic smoke checks passed" in proc.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_report_export_node_smoke() -> None:
    assert EXPORT_SCRIPT.is_file(), f"missing {EXPORT_SCRIPT}"
    proc = subprocess.run(
        ["node", str(EXPORT_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"report_export smoke failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "all report_export smoke checks passed" in proc.stdout
