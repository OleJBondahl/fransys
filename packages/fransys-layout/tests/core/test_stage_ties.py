"""A stage's result does not depend on how ids are spelled or on input order.

Renaming ids by a map that keeps natural_key rank, then mapping the result back, must change
nothing; so must reversing the input tuples. Catches a sort or tie on a lexical or length order.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core.jsonform import to_plain
from fransys_layout.core.keys import natural_key

from .stage_cases import STAGE_CASES

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core.values import PlacementProblem

SCHEMES: tuple[tuple[Callable[[int], str], Callable[[int], str]], ...] = (
    (lambda r: f"S{r}", lambda r: f"N{r}"),
    (lambda r: f"Q{r:04d}", lambda r: f"W{r:04d}"),
    (lambda r: f"Dev{r}Z", lambda r: f"line_{r}_extra_long"),
)


def _ranked(ids: set[str]) -> dict[str, int]:
    return {i: r for r, i in enumerate(sorted(ids, key=natural_key))}


def _id_maps(prob: PlacementProblem, scheme: int) -> dict[str, str]:
    sym_name, net_name = SCHEMES[scheme]
    syms = _ranked({s.id for s in prob.symbols})
    others = {n.id for n in prob.nets} | {n.bundle.id for n in prob.nets if n.bundle}
    return {i: sym_name(r) for i, r in syms.items()} | {
        i: net_name(r) for i, r in _ranked(others).items()
    }


def _rename(prob: PlacementProblem, ids: dict[str, str]) -> PlacementProblem:
    syms = tuple(replace(s, id=ids[s.id]) for s in prob.symbols)
    nets = tuple(
        replace(
            n,
            id=ids[n.id],
            pins=tuple(replace(p, sym=ids[p.sym]) for p in n.pins),
            bundle=replace(n.bundle, id=ids[n.bundle.id]) if n.bundle else None,
        )
        for n in prob.nets
    )
    return replace(prob, symbols=syms, nets=nets)


def _text(result: object, back: dict[str, str]) -> str:
    """The result as JSON text with every id token in `back` replaced, longest first."""
    text = json.dumps(to_plain(result), sort_keys=True)
    if not back:
        return text
    names = "|".join(re.escape(k) for k in sorted(back, key=lambda k: (-len(k), k)))
    token = re.compile(rf"(?<![A-Za-z0-9])({names})(?![A-Za-z0-9])")
    return token.sub(lambda m: back[m.group(1)], text)


@pytest.mark.parametrize("scheme", range(len(SCHEMES)))
@pytest.mark.parametrize(("name", "make", "run"), STAGE_CASES, ids=[c[0] for c in STAGE_CASES])
def test_a_stage_does_not_depend_on_how_ids_are_spelled(
    name: str, make: Callable[[], PlacementProblem], run: Callable[..., object], scheme: int
) -> None:
    """Natural-rank-preserving renames, mapped back, give the original result.

    A stage that sorts or ties ids lexically, by length or by prefix gives another result.
    """
    prob = make()
    ids = _id_maps(prob, scheme)
    assert len(prob.symbols) >= 12 and len(prob.nets) >= 12, name  # noqa: PT018  # one size guard
    back = {new: old for old, new in ids.items()}
    renamed = _text(run(_rename(prob, ids)), back)
    assert renamed == _text(run(prob), {})


@pytest.mark.parametrize(("name", "make", "run"), STAGE_CASES, ids=[c[0] for c in STAGE_CASES])
def test_a_stage_does_not_depend_on_input_order(
    name: str, make: Callable[[], PlacementProblem], run: Callable[..., object]
) -> None:
    """Reversing the symbol and net tuples changes nothing.

    Input order is a tie-break a stage must not use; natural_key is the one.
    """
    prob = make()
    flipped = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    assert _text(run(flipped), {}) == _text(run(prob), {}), name
