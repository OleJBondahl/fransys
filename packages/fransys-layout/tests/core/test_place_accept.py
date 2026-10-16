"""Stage 5, y: alignments kept one at a time in priority order, each drop named."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Options
from fransys_layout.core.constraints import Graph
from fransys_layout.core.place import place_pages
from fransys_layout.core.place_accept import accept, trial
from fransys_layout.core.place_align import Align, page_aligns
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import YCycleError, _settle, _spans, _y_graph

from . import align_fixtures as fx
from .conftest import MARKER_BOX
from .pipeline_fixtures import cut_of
from .test_place_plants import lamp_ring, ring_fan
from .test_place_x import env_of
from .test_place_y import solved


def _base(prob: object) -> tuple[Graph, tuple[Align, ...]]:
    env = env_of(prob)  # ty: ignore[invalid-argument-type] - a PlacementProblem
    x, _ = place_x(env)
    spans = _spans(env, x)
    tangled, _ = _settle(env, spans, {}, {})
    return _y_graph(env, spans, tangled, {}, {})[0], tuple(page_aligns(env))


def test_all_aligns_that_hold_solve_in_one_pass() -> None:
    """The one-pass y equals the y of adding the aligns one by one."""
    base, found = _base(fx.two_band_columns())
    result = accept(base, found)
    assert result is not None
    assert result.kept == found
    assert result.dropped == ()
    y = None
    for i in range(1, len(found) + 1):
        y = trial(base, found[:i])
    assert result.y == y
    assert result.y != trial(base, ())


def _findings(prob: object) -> list[tuple[str, str | None]]:
    _, y, findings = solved(prob)  # ty: ignore[invalid-argument-type] - a PlacementProblem
    assert y
    return [(f.code, f.subject) for f in findings]


def test_a_band_that_contradicts_a_trunk_is_dropped_and_the_row_group_holds() -> None:
    """Hub h and leg l2 share a band: the hub would stand on its own trunk. The group u/v stays."""
    env, y, findings = solved(fx.band_against_trunk("X1"))
    assert [(f.code, f.subject) for f in findings] == [("ALIGN_DROPPED", "rank 1, row 0")]
    assert "band" in findings[0].text
    assert fx.pin_y(env, y, "u1", "n") == fx.pin_y(env, y, "v1", "n")
    assert y[_node(env, "h")] != y[_node(env, "l2")]
    _, free, _ = solved(fx.band_against_trunk(None))
    assert fx.pin_y(env, free, "u1", "n") != fx.pin_y(env, free, "v1", "n")


def _node(env: object, sym: str) -> str:
    col, li, i = next(fx._cells_of(env, sym))  # ty: ignore[invalid-argument-type] - a PageEnv
    return f"cell:{col}:{li}:{i}"


def test_a_band_that_squeezes_a_driver_onto_its_trunk_is_dropped() -> None:
    assert _findings(fx.band_squeezes_driver()) == [("ALIGN_DROPPED", "rank 1, row 0")]


def test_a_band_the_trunk_refuses_is_dropped() -> None:
    """Graph.equal refuses the band (the legs differ in height): a drop, never a raise."""
    assert _findings(fx.band_trunk_refuses()) == [("ALIGN_DROPPED", "rank 1, row 0")]


def _line(*items: tuple[str, int]) -> tuple[tuple[tuple[str, int], ...], ...]:
    return (tuple(items),)


def _three() -> tuple[Graph, list[Align]]:
    """Mate a=c, row group c=d, band a=d+5: the band contradicts the first two together."""
    g = Graph()
    g.after("a", "b", 8)
    found = [
        Align("mate", "m", _line(("a", 0), ("c", 0))),
        Align("row_group", "r", _line(("c", 0), ("d", 0))),
        Align("band", "b", _line(("a", 0), ("d", 5))),
    ]
    return g, found


def test_classes_drop_in_priority_order() -> None:
    """The later item gives way: the band here, the mate when the band comes first."""
    g, found = _three()
    result = accept(g, found)
    assert result is not None
    assert [a.kind for a in result.dropped] == ["band"]
    flipped = accept(g, [found[2], found[1], found[0]])
    assert flipped is not None
    assert [a.kind for a in flipped.dropped] == ["mate"]


def test_each_class_that_contradicts_is_dropped_with_its_finding_in_keep_order() -> None:
    assert _findings(fx.all_three_contradict()) == [
        ("ALIGN_DROPPED", "gp.n/p.s"),
        ("ALIGN_DROPPED", "R1"),
        ("ALIGN_DROPPED", "rank 1, row 0"),
    ]


def test_nothing_is_dropped_when_every_class_holds() -> None:
    assert _findings(fx.two_band_columns()) == []


def test_a_page_the_stacks_and_trunks_contradict_alone_still_raises_ycycleerror() -> None:
    prob = lamp_ring()
    syms = tuple(replace(s, band=1) if s.id in ("a", "c") else s for s in prob.symbols)
    prob = replace(prob, symbols=syms)
    cut = cut_of(prob)
    ring = replace(cut.flow, fans=(ring_fan(cut.flow),), cross_links=())
    with pytest.raises(YCycleError):
        place_pages(replace(cut, flow=ring), prob, Options(marker=MARKER_BOX))


def test_one_finding_per_dropped_item_names_it() -> None:
    _, _, findings = solved(fx.all_three_contradict())
    assert len(findings) == 3
    assert [f.subject in f.text for f in findings if f.subject] == [True, True, True]
    assert findings[0].text.startswith("mate ")
    assert findings[1].text.startswith("row group ")
    assert findings[2].text.startswith("band ")


def test_a_mate_across_rows_or_with_a_box_is_named_not_skipped() -> None:
    assert _findings(fx.mate_across_rows()) == [("ALIGN_DROPPED", "p.s/r.n")]
    assert _findings(fx.mate_with_box()) == [("ALIGN_DROPPED", "A1.p1/k3.n")]
