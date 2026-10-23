"""`python -m fransys parts-module LIBRARY OUT` writes the module `parts_module` returns."""

import subprocess
import sys

import fransys
from fransys.__main__ import main
from fransys._codes import BY_CODE
from fransys._help import help_text
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


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- fixed test arguments
        [sys.executable, "-m", "fransys", *args], capture_output=True, text=True, check=False
    )


def test_help_of_a_near_miss_exits_1_and_suggests_the_name() -> None:
    run = _run("help", "wrte")
    assert run.returncode == 1
    assert "no such name or code: wrte" in run.stdout
    assert "did you mean:" in run.stdout
    assert "write" in run.stdout


def test_help_of_a_name_exits_0() -> None:
    run = _run("help", "write")
    assert run.returncode == 0
    assert run.stdout.startswith("fr.write(")


def test_help_of_a_code_prints_its_severity() -> None:
    run = _run("help", "SHEET_FORMAT_UNUSED")
    assert run.returncode == 0
    assert BY_CODE["SHEET_FORMAT_UNUSED"].severities[0].name in run.stdout


def test_help_with_no_key_or_two_keys_prints_usage_and_exits_2() -> None:
    for args in (("help",), ("help", "a", "b")):
        run = _run(*args)
        assert run.returncode == 2
        assert "usage: python -m fransys parts-module" in run.stderr
        assert "help KEY" in run.stderr


def test_a_name_wins_over_a_code() -> None:
    assert not set(fransys.__all__) & set(BY_CODE)
    text, code = help_text("write")
    assert code == 0
    assert text.startswith("fr.write(")
