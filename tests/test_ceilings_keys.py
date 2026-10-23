"""Every `ceilings.toml` key names a file and, for `path::name`, a function or class in it.

A key left behind when its function is renamed or removed raises nothing and hides a dead limit
(spec CONSOLIDATE lane L14).
"""

import tomllib
lazy from pathlib import Path

from _export_signature import is_export
from gate_scan import ROOT, stale_ceiling_keys


def test_every_ceilings_key_names_something() -> None:
    ceilings = tomllib.loads((ROOT / "ceilings.toml").read_text())
    assert not stale_ceiling_keys(ceilings, skip_missing=is_export())


def test_a_key_naming_a_missing_function_or_file_fails(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text(
        "class C:\n    def f(self) -> None: ...\n\ndef g() -> None: ...\n"
    )
    good = {"statements": {"m.py::g": 1, "m.py::C.f": 2}, "limits": {"statements": 15}}
    assert stale_ceiling_keys(good, tmp_path) == []
    bad = {"statements": {"m.py::nothing": 1, "gone.py::g": 1}}
    problems = stale_ceiling_keys(bad, tmp_path)
    assert "m.py has no nothing; delete the key" in problems[0]
    assert "gone.py does not exist" in problems[1]


def test_the_export_skips_a_key_whose_file_is_absent_and_still_checks_the_rest(
    tmp_path: Path,
) -> None:
    """R462: the export lacks the private docs, so only keys whose path exists are checked."""
    (tmp_path / "m.py").write_text("def g() -> None: ...\n")
    ceilings = {"md_tokens": {"docs/private.md": 1}, "statements": {"m.py::nothing": 1}}
    assert len(stale_ceiling_keys(ceilings, tmp_path)) == 2
    problems = stale_ceiling_keys(ceilings, tmp_path, skip_missing=True)
    assert len(problems) == 1
    assert "m.py has no nothing" in problems[0]
