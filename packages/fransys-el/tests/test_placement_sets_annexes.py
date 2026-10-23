"""A scoped problem keeps the annexes of its own symbols and drops the others' (TEXT-STAGE)."""

import tempfile
from pathlib import Path

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, symbol_kit
from fransys_el.placement_sets import DrawingScope, restrict

from electrical_symbols import LIBRARY


def _problem():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    third = d.device("K3", "DEMO-RLY-2CO-24")
    d.detail.wire(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    d.detail.wire(second.coil["A2"], third.coil["A1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    drafts = (d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))
    model = fr.build(*drafts).model
    return build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)[0]


def test_a_scoped_problem_keeps_its_own_annexes_and_drops_the_others() -> None:
    problem = _problem()
    ids = [s.id for s in problem.symbols]
    owners = {a.owner for a in problem.annexes}
    assert len(ids) == 3
    assert set(ids) <= owners
    scoped = restrict(problem, DrawingScope(None, None, frozenset(ids[:2])))
    assert [s.id for s in scoped.symbols] == ids[:2]
    assert [a.owner for a in scoped.annexes] == ids[:2]
