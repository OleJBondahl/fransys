"""Keyword tables (API-CLARITY C3, A3): each public call has a table that matches its signature.

The guide pages `keywords-*.md` hold one table per call: keyword, default, effect, example.
The keywords equal the signature's named parameters, each default cell equals the signature's
default and no effect cell is empty. `d.layout.profile` and `d.layout.sheet` keep their tables
in `layout-numbers.md`.
"""

import enum
import inspect
import re
from pathlib import Path

import fransys as fr
from test_tier_words import namespaced, tiered

GUIDE = Path(fr.__file__).parent / "guide"
PAGES = ("keywords-design.md", "keywords-handles.md", "keywords-output.md")
EXEMPT = {"d.layout.profile", "d.layout.sheet"}
NAMED = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
_HEAD = re.compile(r"^## `([^`]+)`$")


def calls() -> dict[str, object]:
    found = dict(tiered())
    found |= {k: v for k, v in namespaced().items() if not k.startswith("fr.derive.")}
    return {k: v for k, v in found.items() if k not in EXEMPT}


def named(call: object) -> list[inspect.Parameter]:
    params = inspect.signature(call).parameters.values()  # ty: ignore[invalid-argument-type] # call is a function
    return [p for p in params if p.kind in NAMED and p.name not in ("self", "cls")]


def default_cell(p: inspect.Parameter) -> str:
    v = p.default
    if v is inspect.Parameter.empty:
        return "required"
    if v is Ellipsis:
        return "`...`"
    if isinstance(v, enum.Enum):
        return (
            f"`fr.{v.name}`" if getattr(fr, v.name, None) is v else f"`{type(v).__name__}.{v.name}`"
        )
    return f"`{v!r}`"


def sections() -> dict[str, list[list[str]]]:
    """Each call heading to the cells of its table rows, header and rule excluded."""
    found: dict[str, list[list[str]]] = {}
    for page in PAGES:
        current = None
        for line in (GUIDE / page).read_text().splitlines():
            head = _HEAD.match(line)
            if head:
                current = head.group(1)
                assert current not in found, f"two sections for {current}"
                found[current] = []
            elif current and line.startswith("| ") and not line.startswith("| keyword"):
                found[current].append([c.strip() for c in line.strip().strip("|").split(" | ")])
    return found


def test_every_public_call_has_a_section_and_no_other_section_exists():
    assert set(sections()) == set(calls()), set(sections()) ^ set(calls())


def test_table_keywords_equal_the_signatures_named_parameters():
    table = sections()
    bad = {
        k: ([r[0] for r in table[k]], [f"`{p.name}`" for p in named(v)])
        for k, v in calls().items()
        if [r[0] for r in table[k]] != [f"`{p.name}`" for p in named(v)]
    }
    assert not bad, f"table keywords differ from the signature: {bad}"


def test_table_defaults_equal_the_signatures_defaults():
    table = sections()
    bad = {}
    for k, v in calls().items():
        want = [default_cell(p) for p in named(v)]
        got = [r[1] for r in table[k]]
        if got != want:
            bad[k] = (got, want)
    assert not bad, f"default cells differ from the signature: {bad}"


def test_every_row_has_an_effect_and_an_example():
    empty = [(k, r[0]) for k, rows in sections().items() for r in rows if len(r) != 4 or not all(r)]
    assert not empty, f"rows with an empty or missing cell: {empty}"


def test_the_collector_sees_calls():
    assert {"fr.build", "d.device", "d.layout.symbol", "Cable.core"} <= set(calls())
    assert "d.layout.profile" not in calls()
