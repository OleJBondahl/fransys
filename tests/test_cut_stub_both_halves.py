"""WHERE-WIRED (R404, R407): one page one wire, a cut a reference pair, out a stub in each unit.

A conductor that crosses a unit boundary draws a stub in each unit it touches.

Each unit's side shows its own stub, so no cable has only one half of its pair drawn. Checked on
the core layout of the machine panel (32 channels), the panel with a DI card and the MCC.
"""

import importlib
import sys
from collections import defaultdict
from pathlib import Path

import fransys as fr
import pytest
from _direct_case import built_with_unlaid, laid_again
from fransys_el import lay_out_core

ROOT = Path(__file__).resolve().parent.parent
CASES = {"machine_panel": {"channels": 32}, "panel_di16p": {}, "mcc": {}}


def _solved(name: str) -> list[tuple[object, object]]:
    """(problem, CoreLayout) of every core solve the case's layout step makes."""
    sys.path.insert(0, str(ROOT / "internal"))
    module = importlib.import_module(f"placement_corpus.standard.{name}")
    _, unlaid = built_with_unlaid(lambda: fr.build(*module.design(**CASES[name])))
    solved = []
    real = lay_out_core.solve

    def spy(problem, options, *args, **kwargs):
        solved.append((problem, real(problem, options, *args, **kwargs)))
        return solved[-1][1]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(lay_out_core, "solve", spy)
        laid_again(unlaid)
    return solved


@pytest.fixture(
    scope="module",
    params=[pytest.param(n, marks=pytest.mark.private_input) for n in CASES],  # R462
)
def solved(request: pytest.FixtureRequest):
    return request.param, _solved(request.param)


@pytest.mark.rule("WHERE-WIRED")
def test_a_crossing_net_has_a_stub_in_every_unit_it_touches(solved) -> None:
    name, runs = solved
    missing = []
    for problem, layout in runs:
        unit_of = {s.id: s.unit for s in problem.symbols}
        stubbed = defaultdict(set)
        for ref in layout.references:
            if ref.kind.value == "stub":
                stubbed[ref.net].update(unit_of[e.pin.sym] for e in ref.ends if e.pin)
        for net in problem.nets:
            units = {unit_of[p.sym] for p in net.pins}
            if net.crosses_unit and len(units) > 1:
                missing += [(net.id[:8], u) for u in units - stubbed[net.id]]
    assert missing == [], name


@pytest.mark.rule("WHERE-WIRED")
def test_a_tag_pair_joins_two_pages_never_one(solved) -> None:
    """One page one wire: a net on one page is a wire, so a row cut plans no tag (R404)."""
    name, runs = solved
    same_page = [
        (ref.net[:8], ref.ends[0].page)
        for _, layout in runs
        for ref in layout.references
        if ref.kind.value == "tag" and len({e.page for e in ref.ends}) == 1
    ]
    assert same_page == [], name
