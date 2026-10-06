"""`scripts/lean_ceilings.py`: parsing, rendering, `check`, `lower`, `first_run`.

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. There is no real `ceilings.toml` read
anywhere in this file; every case builds its own small TOML text or in-memory mapping by hand.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_ceilings", ROOT / "scripts" / "lean_ceilings.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_ceilings.py"
    raise ImportError(msg)
lean_ceilings = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_ceilings
_spec.loader.exec_module(lean_ceilings)


# --- check / lower / first_run: contract, each with a can-fail probe -----------------------


def test_check_unlisted_site_over_limit_fails():
    """A site over its limit, unlisted, fails (`check`, `listed=False`)."""
    violations = lean_ceilings.check({"pkg/a.py::f": 20}, ceilings={}, limit=15)
    assert violations == (
        lean_ceilings.Violation(site="pkg/a.py::f", measured=20, limit=15, listed=False),
    )


def test_check_listed_site_grown_over_ceiling_fails():
    """A listed site grown by one over its own ceiling fails (`check`, `listed=True`)."""
    violations = lean_ceilings.check({"pkg/a.py::f": 21}, ceilings={"pkg/a.py::f": 20}, limit=15)
    assert violations == (
        lean_ceilings.Violation(site="pkg/a.py::f", measured=21, limit=20, listed=True),
    )


def test_lower_never_raises_and_check_still_fails():
    """`lower` keeps the old ceiling when measured grew above it; `check` against that unchanged
    ceilings dict still fails.
    """
    measured = {"pkg/a.py::f": 25}
    ceilings = {"pkg/a.py::f": 20}
    lowered = lean_ceilings.lower(measured, ceilings)
    assert lowered == {"pkg/a.py::f": 20}
    assert lean_ceilings.check(measured, lowered, limit=15) == (
        lean_ceilings.Violation(site="pkg/a.py::f", measured=25, limit=20, listed=True),
    )


def test_lower_deletes_within_limit_and_shrinks_still_over():
    """`lower` deletes an entry now within limit and shrinks one that shrank but stays over."""
    ceilings = {"pkg/a.py::f": 20, "pkg/b.py::g": 30}
    measured = {"pkg/b.py::g": 22}
    lowered = lean_ceilings.lower(measured, ceilings)
    assert "pkg/a.py::f" not in lowered
    assert lowered["pkg/b.py::g"] == 22


def test_exempt_site_never_appears_anywhere():
    """An `[exempt]` site never appears in `check`'s violations, `lower`'s output, or
    `first_run`'s output, regardless of its measured value.
    """
    measured = {"pkg/a.py::f": 999}
    ceilings = {"pkg/a.py::f": 20}
    exempt = {"pkg/a.py::f": "generated (owner-0001)"}
    assert lean_ceilings.check(measured, ceilings, limit=15, exempt=exempt) == ()
    assert lean_ceilings.lower(measured, ceilings, exempt=exempt) == {}
    assert lean_ceilings.first_run(measured, exempt=exempt) == {}


# --- load_ceilings / render_ceilings: round trips, no probe needed -------------------------


def test_load_ceilings_round_trips(tmp_path):
    """`load_ceilings` on a small literal TOML string round-trips into the expected fields."""
    text = """[limits]
statements = 15
sentence_words = 30

[statements]
"pkg/a.py::f" = 20

[exempt]
"pkg/b.py::g" = "generated (test-0001)"
"""
    path = tmp_path / "ceilings.toml"
    path.write_text(text, encoding="utf-8")

    parsed = lean_ceilings.load_ceilings(path)

    assert parsed.limits == {"statements": 15, "sentence_words": 30}
    assert parsed.sections == {"statements": {"pkg/a.py::f": 20}}
    assert parsed.exempt == {"pkg/b.py::g": "generated (test-0001)"}


def _table_block(text: str, header: str) -> str:
    """The block starting with `header` (e.g. `"[nested_defs]"`) out of `render_ceilings` text."""
    blocks = text.strip("\n").split("\n\n")
    (block,) = (block for block in blocks if block.startswith(header))
    return block


def test_render_ceilings_round_trip_stable(tmp_path):
    """`render(load(render(load(text))))` equals `render(load(text))`: no reordering."""
    text = """[limits]
statements = 15
sentence_words = 30

[statements]
"pkg/a.py::f" = 20
"pkg/c.py::h" = 25

[nested_defs]
"pkg/b.py::g" = 2

[exempt]
"pkg/z.py::q" = "generated (test-0001)"
"""
    path = tmp_path / "ceilings.toml"
    path.write_text(text, encoding="utf-8")

    once = lean_ceilings.render_ceilings(lean_ceilings.load_ceilings(path))
    path.write_text(once, encoding="utf-8")
    twice = lean_ceilings.render_ceilings(lean_ceilings.load_ceilings(path))

    assert once == twice


def test_render_ceilings_isolates_sections_on_rename_and_delete(tmp_path):
    """Renaming or deleting a key in one section leaves every other section's rendered text
    byte-identical.
    """
    text = """[limits]
statements = 15

[statements]
"pkg/a.py::f" = 20
"pkg/c.py::h" = 25

[nested_defs]
"pkg/b.py::g" = 2
"""
    path = tmp_path / "ceilings.toml"
    path.write_text(text, encoding="utf-8")
    original = lean_ceilings.load_ceilings(path)
    before = lean_ceilings.render_ceilings(original)
    before_nested_defs = _table_block(before, "[nested_defs]")
    before_limits = _table_block(before, "[limits]")

    renamed_statements = dict(original.sections["statements"])
    renamed_statements["pkg/a.py::f2"] = renamed_statements.pop("pkg/a.py::f")
    renamed = dataclasses.replace(
        original, sections={**original.sections, "statements": renamed_statements}
    )
    after_rename = lean_ceilings.render_ceilings(renamed)
    assert _table_block(after_rename, "[nested_defs]") == before_nested_defs
    assert _table_block(after_rename, "[limits]") == before_limits

    deleted_statements = dict(original.sections["statements"])
    del deleted_statements["pkg/c.py::h"]
    deleted = dataclasses.replace(
        original, sections={**original.sections, "statements": deleted_statements}
    )
    after_delete = lean_ceilings.render_ceilings(deleted)
    assert _table_block(after_delete, "[nested_defs]") == before_nested_defs
    assert _table_block(after_delete, "[limits]") == before_limits


def test_render_ceilings_omits_empty_section():
    """An empty section's header is left out entirely, never `[section]` with nothing under it."""
    file = lean_ceilings.CeilingsFile(
        limits={"statements": 15}, sections={"surface_docstring_lines": {}}, exempt={}
    )
    rendered = lean_ceilings.render_ceilings(file)
    assert "[surface_docstring_lines]" not in rendered
    assert "[exempt]" not in rendered


def test_first_run_never_mutates_measured():
    """`first_run` never mutates its `measured` argument."""
    measured = {"pkg/a.py::f": 30, "pkg/b.py::g": 40}
    before = dict(measured)
    lean_ceilings.first_run(measured, exempt={"pkg/b.py::g": "generated (test-0001)"})
    assert measured == before


# --- is_exempt_under: directory-scope match, independent of check's exact match ------------


def test_is_exempt_under_matches_subtree_not_siblings():
    """A directory-scoped exempt entry covers every file under it (src and tests alike), not a
    sibling package, and `check`'s exact matching stays untouched by the same exempt dict.
    """
    exempt = {
        "packages/fransys-layout": (
            "layout noqa/ty:ignore backfill waits for layout redesign step 5 (LG1, 2026-09-27)"
        )
    }

    assert lean_ceilings.is_exempt_under("packages/fransys-layout/src/x.py::f", exempt)
    assert lean_ceilings.is_exempt_under("packages/fransys-layout/tests/test_x.py::f", exempt)
    assert not lean_ceilings.is_exempt_under("packages/fransys-render/src/x.py::f", exempt)

    site = "packages/fransys-layout/src/x.py::f"
    violations = lean_ceilings.check({site: 20}, ceilings={}, limit=15, exempt=exempt)
    assert violations == (lean_ceilings.Violation(site=site, measured=20, limit=15, listed=False),)
