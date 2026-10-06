"""S12: every run `references` joined lands on one y, on the goldens and the fixtures.

`place` aligns each joined run (`place._align_joins`) on the stacking `references` decided it on
(`place.page_stack`), so it never refuses one. The goldens (the cabinet on the house sheet and on
its 158 mm sheet) join no run today, and neither do the example or a field case; the fixtures
that do carry the proof: a feed fanning to three breakers (the feed XA:1 beside Q3, both N at
their columns' tops: LD9's feeds along the top), the same breakers daisy-chained (level runs
between neighbours), and a strip of 8 terminals wired in a chain (its single-terminal columns
joined along their tops). Measured over every engine run of the layout and root suites on
2026-09-27: 68 joined runs in 43 runs, every one on one y.

Each case builds once (`cache`); the goldens share `narrow_cabinet`'s cached build for 158 mm.
"""

from functools import cache

import pytest
from dd_chain_fixtures import terminal_chain, three_breakers
from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_results

from fransys_layout.engines.schematic.engine import StageResults, stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.kernel import Model, freeze


def _laid_out(model: Model) -> StageResults:
    return stage_results(model, read_inputs(model))[0]


_CASES = {
    "cabinet": lambda: _laid_out(freeze(build_cabinet())),
    "cabinet_narrow": lambda: narrow_results(158)[0],
    "feed_fanning": lambda: _laid_out(three_breakers(daisy=False)),
    "daisy_chain": lambda: _laid_out(three_breakers(daisy=True)),
    "terminal_chain": lambda: _laid_out(terminal_chain(8)),
}


@cache
def _results(case: str) -> StageResults:
    return _CASES[case]()


def _port_ys(results: StageResults) -> list[set[int]]:
    """Each joined run's placed port ys."""
    at = {(p.function, p.drawing_set, p.page, p.column): p for p in results.layout.placed}
    symbol = {
        port.port: (one.function, port.symbol_port) for one in results.drawn for port in one.ports
    }
    found = []
    for run in results.joins:
        ys = set()
        for end in run.ends:
            function, name = symbol[end.port]
            one = at[function, run.drawing_set, run.page, end.column]
            ys.add(one.at.y + next(g.at.y for g in one.geometry.ports if g.name == name))
        found.append(ys)
    return found


@pytest.mark.parametrize("case", sorted(_CASES))
def test_every_joined_run_lands_on_one_y(case: str) -> None:
    """Each run's ports stand on one y as placed; the fixtures do join runs.

    The house-sheet cabinet's case takes about 1 s: its build is its own, one per module
    (`_results`), since no other test of this package lays the cabinet out on the house sheet
    through a shared cache.
    """
    # CAN-FAIL (S12's own): stages/place.py `place`: drop the `_align_joins(...)` call (`place`
    #     then aligns nothing): the feed fanning's XA:1 - Q3:1 (8 G apart) and the terminal
    #     chain's columns (72 G apart) no longer land on one y
    ys = _port_ys(_results(case))
    assert [one for one in ys if len(one) != 1] == []
    if not case.startswith("cabinet"):
        assert ys
