"""`python -m fransys parts-module LIBRARY OUT` writes the module `parts_module` returns."""

import subprocess
import sys

from fransys.__main__ import main
from fransys.parts_module import parts_module


def test_parts_module_command_writes_the_generated_text(tmp_path) -> None:
    out = tmp_path / "gparts.py"
    assert main(["parts-module", "demo_parts", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == parts_module("demo_parts")


def test_a_wrong_command_prints_usage_and_exits_2() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "fransys", "parts-modul"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 2
    assert "usage: python -m fransys parts-module" in run.stderr
