"""`python -m fransys parts-module LIBRARY OUT` writes the module `parts_module` returns."""

import importlib.resources
import subprocess
import sys

import fransys
import fransys_parts
from fransys.__main__ import USAGE, main
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
    run = _run("help", "PAGE_OVERFLOW")
    assert run.returncode == 0
    assert BY_CODE["PAGE_OVERFLOW"].severity.name in run.stdout


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


_LIBRARY_1 = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_PART_1 = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"

[rating]
voltage_ac_v = "500"
"""


def _schema_1_library(tmp_path, part=_PART_1):
    (tmp_path / "pkg" / "parts").mkdir(parents=True)
    (tmp_path / "pkg" / "library.toml").write_text(_LIBRARY_1)
    (tmp_path / "pkg" / "parts" / "p.toml").write_text(part)
    return tmp_path / "pkg"


def test_migrate_parts_rewrites_a_schema_1_library_that_then_lints_clean(tmp_path, capsys) -> None:
    root = _schema_1_library(tmp_path)
    assert "PART_SCHEMA_OLD" in {f.code for f in fransys_parts.lint(root)}
    assert main(["migrate-parts", str(tmp_path)]) == 0
    assert capsys.readouterr().out.count("rewrote ") == 2
    assert 'voltage = [{ nom = "500 V", at = ["AC"] }]' in (root / "parts" / "p.toml").read_text()
    assert not [f for f in fransys_parts.lint(root) if f.severity.name == "ERROR"]


def test_migrate_parts_names_the_file_it_cannot_convert_and_keeps_library_toml(tmp_path, capsys) -> None:
    root = _schema_1_library(tmp_path, _PART_1.replace("[rating]", "[rating"))
    assert main(["migrate-parts", str(tmp_path)]) == 1
    assert "p.toml" in capsys.readouterr().err
    assert (root / "library.toml").read_text() == _LIBRARY_1


def test_the_guide_names_the_migrate_parts_command() -> None:
    page = importlib.resources.files("fransys").joinpath("guide", "parts.md").read_text(encoding="utf-8")
    assert "python -m fransys migrate-parts DIR" in page
    assert "migrate-parts DIR" in USAGE


def test_migrate_parts_given_the_parts_folder_fails_and_names_both_folders(tmp_path, capsys) -> None:
    root = _schema_1_library(tmp_path)
    assert main(["migrate-parts", str(root / "parts")]) == 1
    err = capsys.readouterr().err
    assert str(root / "parts") in err
    assert "library.toml" in err
    assert "schema = 1" in (root / "parts" / "p.toml").read_text()


def test_migrate_parts_refuses_a_pe_bar_part_and_writes_nothing(tmp_path, capsys) -> None:
    bar = _PART_1 + '\n[[function]]\nname = "pe"\nkind = "bar"\nports = [{ name = "1", role = "pe" }]\n'
    root = _schema_1_library(tmp_path, bar)
    assert main(["migrate-parts", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "p.toml" in err
    assert "moving-to-0.22.md#removed-cable-core-fn" in err
    assert (root / "parts" / "p.toml").read_text() == bar
    assert (root / "library.toml").read_text() == _LIBRARY_1
