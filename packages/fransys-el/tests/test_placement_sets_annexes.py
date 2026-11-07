"""A scoped problem keeps the annexes of its own symbols and drops the others' (TEXT-STAGE)."""

import fransys as fr
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_sets import DrawingScope, restrict
from fransys_el.write_findings import kernel_findings
from fransys_el.write_ids import symbol_subjects

from electrical_symbols import LIBRARY
from fransys_layout.core import Finding


def _built():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    third = d.device("K3", "DEMO-RLY-2CO-24")
    d.series(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    d.series(second.coil["A2"], third.coil["A1"], wire=(BU, 0.5))
    d.series(third.coil["A2"], first.coil["A1"], wire=(BU, 0.5))
    drafts = (d, unit_document(cab))
    model = fr.build(*drafts).model
    return model, symbol_kit(model, LIBRARY)


def _problem():
    model, kit = _built()
    return build(model, kit, house(), LIBRARY)[0]


def test_a_scoped_problem_keeps_its_own_annexes_and_drops_the_others() -> None:
    problem = _problem()
    ids = [s.id for s in problem.symbols]
    owners = {a.owner for a in problem.annexes}
    assert len(ids) == 3
    assert set(ids) <= owners
    scoped = restrict(problem, DrawingScope(None, None, frozenset(ids[:2])))
    assert [s.id for s in scoped.symbols] == ids[:2]
    assert [a.owner for a in scoped.annexes] == ids[:2]


def test_a_scoped_problem_keeps_the_far_ends_of_its_own_symbols_even_to_one_outside() -> None:
    """R1128: a far end leaving the set stays, so the cut owes it a carrier."""
    problem = _problem()
    ids = [s.id for s in problem.symbols]
    assert {p.sym for pair in problem.facts.far_ends for p in pair} == set(ids)
    scoped = restrict(problem, DrawingScope(None, None, frozenset(ids[:2])))
    assert {near.sym for near, _ in scoped.facts.far_ends} == set(ids[:2])
    assert any(far.sym == ids[2] for _, far in scoped.facts.far_ends)


def test_an_annex_finding_names_the_designation_not_the_symbol_key() -> None:
    """Can fail by printing the core key: a key is internal (R1084), the finding says `annex of -K1`."""
    model, kit = _built()
    symbols = symbol_subjects(model, kit)
    key = next(iter(symbols))
    core = Finding("ANNEX_UNPLACED", f"annex of {key} on page 1 is blocked by 2 things", 1, key)
    (found,) = kernel_findings(model, [core], symbols, {})
    assert found.message == "annex of -K1 on page 1 is blocked by 2 things"
