"""The fact registry: every fact carries a kind tag, and an electrical or physical one a source.

`fact_problems` takes the facts, so the can-fail tests feed it synthetic ones. The repo test
imports the engine so every fact has registered, then checks the whole registry.
"""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import fransys_layout.engines.schematic  # noqa: F401 -- importing registers every fact
from fransys_layout import conventions
from fransys_layout.conventions import (
    FACTS,
    KINDS,
    SOURCED_KINDS,
    Fact,
    Order,
    Table,
    fact,
    problems,
)


def fact_problems(facts: dict[str, Fact]) -> list[str]:
    """Each fact with no valid kind tag, and each electrical or physical one with no source."""
    found = [
        f"{n}: kind {f.kind!r} is not one of {KINDS}"
        for n, f in facts.items()
        if f.kind not in KINDS
    ]
    found += [
        f"{n}: {f.kind} fact names no source"
        for n, f in facts.items()
        if f.kind in SOURCED_KINDS and not f.source
    ]
    found += [
        f"{n}: no summary line" for n, f in facts.items() if not (f.func.__doc__ or "").strip()
    ]
    return found


def _fake(kind: str, source: str = "", doc: str = "s") -> Fact:
    def func(_subject: object) -> bool:
        return True

    func.__doc__ = doc
    return Fact("x", kind, source, None, func)


def test_every_registered_fact_is_tagged_and_sourced() -> None:
    """The real registry has no untagged fact and no unsourced electrical or physical one."""
    assert fact_problems(FACTS) == []


def test_a_fact_without_a_kind_tag_is_reported() -> None:
    """Dropping the tag from a fact fails the check."""
    assert fact_problems({"x": _fake("")}) == [f"x: kind '' is not one of {KINDS}"]


def test_an_electrical_fact_without_a_source_is_reported() -> None:
    """An electrical or physical fact must name its source; a drawing fact need not."""
    facts = {"a": _fake("electrical"), "b": _fake("physical"), "c": _fake("drawing")}
    assert fact_problems(facts) == [
        "a: electrical fact names no source",
        "b: physical fact names no source",
    ]


def test_a_fact_without_a_summary_is_reported() -> None:
    """Every fact has one summary line, its docstring."""
    assert fact_problems({"x": _fake("drawing", doc="")}) == ["x: no summary line"]


def test_the_decorator_stores_kind_source_values_and_the_docstring_line() -> None:
    """`fact` registers the function with its tags, and a second registration is refused."""

    @fact("test_only_fact", kind="physical", source="a datasheet field", values=("a", "b"))
    def _f(_subject: object) -> str:
        """Summary line.

        More text.
        """
        return "a"

    try:
        got = FACTS["test_only_fact"]
        assert (got.kind, got.source, got.values, (got.func.__doc__ or "").splitlines()[0]) == (
            "physical",
            "a datasheet field",
            ("a", "b"),
            "Summary line.",
        )
        with pytest.raises(ValueError, match="registered twice"):
            fact("test_only_fact")(_f)
    finally:
        del FACTS["test_only_fact"]


def test_every_table_names_registered_facts_and_values() -> None:
    """Each table of every conventions module validates against the registry, as at load."""
    found = []
    for info in pkgutil.iter_modules(conventions.__path__):
        module = importlib.import_module(f"fransys_layout.conventions.{info.name}")
        found += [
            p
            for value in vars(module).values()
            if isinstance(value, Table | Order)
            for p in problems(value, FACTS)
        ]
    assert found == []


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "fransys_layout"


def unused_facts(names: set[str], src_root: Path) -> list[str]:
    """Facts whose name appears as a string only once under `src_root`: the registration itself.

    A table row, a `FACTS["name"]` read or any other string use of the name is a second sighting.
    """
    seen: dict[str, int] = dict.fromkeys(names, 0)
    for path in src_root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in seen
            ):
                seen[node.value] += 1
    return sorted(name for name, count in seen.items() if count < 2)


def test_every_registered_fact_is_used_by_a_row_or_read_by_name() -> None:
    """The dead-fact check that vulture no longer makes: a fact nothing names is reported."""
    assert unused_facts(set(FACTS), SRC_ROOT) == []


def test_a_fact_named_only_by_its_registration_is_reported(tmp_path: Path) -> None:
    """One sighting is the registration; a second string use clears it."""
    (tmp_path / "a.py").write_text('@fact("lonely")\ndef f(): ...\n@fact("used")\ndef g(): ...\n')
    (tmp_path / "b.py").write_text('ROWS = ("used",)\n')
    assert unused_facts({"lonely", "used"}, tmp_path) == ["lonely"]
