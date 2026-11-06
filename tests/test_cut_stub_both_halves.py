"""WHERE-WIRED (R404, R407): one page one wire, a cut a reference pair, out a stub in each unit.

A conductor that crosses a unit boundary draws a stub in each unit it touches, unless the net is
drawn to its far end on the page (MARKER-FREE-SIDE, M1): the wire is the reference there.
"""

import importlib
from collections import defaultdict

import pytest
from _direct_case import built_with_unlaid, laid_again
from fransys_el import lay_out_core

WRAPS = {  # census 2026-10-25: the 7 builds of R847
    "machine_panel": 0,  # BRIDGE-NOT-DRAWN (R1145): a bridged rail draws no cut, was 1 (RAIL-FLAG R921: was 0)
    "panel_di16p": 1,  # SUPPLY-SLOT (R1605): was 2 (BRIDGE-NOT-DRAWN R1145: was 3)
    "mcc": 0,
    "distribution_board": 2,  # R1730: ARROW row wraps of net f:U1-F1, at cuts 4 and 16; was 0
    "distribution_board_large": 5,  # R1800 (KI-705, looks): ARROW row wraps of f:U1-F1 cuts 51, 63, 72, 83, f:U1-F9 cut 83; was 0
    "skid_v48_m6": 3,  # TEXT-IN-LOOP 1 (R1450): a blocked label widens its gap in the recut; was 2
    "demo-skid": 1,
}
SIZES = {"machine_panel": {"channels": 32}}


def _circuit(name: str):
    """The corpus runner's circuit of a build: a standard module, a large size, or the demo skid."""
    run = importlib.import_module("placement_corpus.run")
    if name == "demo-skid":
        return (run.SKID.name, run.load(run.SKID, "demo_skid_census"), {}, {})
    found = {c[0]: c for s in ("standard", "large") for c in run.circuits(s)}
    base = found[name]
    return (*base[:2], SIZES.get(name, base[2]), base[3])


def _solved(name: str) -> list[tuple[object, object]]:
    """(problem, CoreLayout) of every core solve the case's layout step makes."""
    run = importlib.import_module("placement_corpus.run")
    _, unlaid = built_with_unlaid(lambda: run.build(name, _circuit(name)))
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
    params=[pytest.param(n, marks=pytest.mark.private_input) for n in WRAPS],  # R462
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
            units = {unit_of[p.sym] for p in net.pins if p not in layout.drawn}
            if net.crosses_unit and len(units) > 1:
                missing += [(net.id[:8], u) for u in units - stubbed[net.id]]
    assert missing == [], name


@pytest.mark.rule("ROW-WRAP")
def test_a_same_page_reference_is_a_row_wrap_or_a_card_halves_tag(solved) -> None:
    """Only ROW-WRAP (an arrow pair between two bands) and CROSS-HALF-TAGS (one box's halves) join one page (R847)."""
    name, runs = solved
    odd, wraps = [], 0
    for _, layout in runs:
        for ref in layout.references:
            if ref.kind.value == "stub" or len({e.page for e in ref.ends}) != 1:
                continue
            wrap = ref.kind.value == "arrow" and len({e.row for e in ref.ends}) == len(ref.ends)
            halves = ref.kind.value == "tag" and len({e.pin.sym for e in ref.ends if e.pin}) == 1
            wraps += wrap
            if not (wrap or halves):
                odd.append((ref.net[:8], ref.kind.value, ref.cut))
    assert odd == [], name
    assert wraps == WRAPS[name], name
