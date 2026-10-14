"""SERIES-GAPS S8 (A10): a selector changeover is entered at its throws and drawn turned."""

from typing import NamedTuple

import fransys as fr
import pytest

from fransys_layout.engines.schematic.read.functions import function_spec
from fransys_layout.stages.resolve import throw_port
from fransys_model.derive.indexes import build_indexes
from fransys_model.layout import Orientation, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions


class _Io(NamedTuple):
    """No boundary."""


def _selector(c) -> None:
    """Supply A through QA to the make throws, commons to M1; supply B through QB to the breaks."""
    xa, xb = c.terminal_strip("XA", "DEMO-TB-2.5"), c.terminal_strip("XB", "DEMO-TB-2.5")
    a = c.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
    b = c.ac_supply("B", "230", xb[1], xb[2], xb[3], names=("B_L1", "B_L2", "B_L3"))
    qa, qb = c.device("QA", "DEMO-MCB-3P"), c.device("QB", "DEMO-MCB-3P")
    q1, m1 = c.device("Q1", "DEMO-SEL-3P-24"), c.device("M1", "DEMO-MOTOR-4KW")
    c.series(a, qa.element, q1.co.no, m1, wire=2.5)
    c.series(b, qb.element, q1.co.nc, wire=2.5)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    """The selector circuit in a unit, built with its cabinet schematic (one build per module)."""
    unit = fr.unit(
        "sel", revision=1, interface_version=1, date="2026-10-14", text="First", by="XX"
    )(lambda c: (_selector(c), _Io())[1])
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    cover = tmp_path_factory.mktemp("selector") / "cover.md"
    cover.write_text("# Selector\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "sel", cover=cover))


def test_supply_a_reaches_the_make_throws_and_the_commons_feed_the_motor(built) -> None:
    ends = {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(built.model)}
    for pole, (line, motor) in enumerate((("2", "U"), ("4", "V"), ("6", "W")), start=1):
        assert frozenset((f"-U1-QA:{line}", f"-U1-Q1:{pole}4")) in ends
        assert frozenset((f"-U1-QB:{line}", f"-U1-Q1:{pole}2")) in ends
        assert frozenset((f"-U1-Q1:{pole}1", f"-U1-M1:{motor}")) in ends


def test_the_selector_is_drawn_turned_with_its_commons_toward_the_load(built) -> None:
    model = built.model
    (placed,) = (
        p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].key[-3:] == ("Q1", "fn", "co")
    )
    assert placed.orientation in {Orientation.R180, Orientation.MR180}


def test_each_pole_binds_its_own_symbol_throws_in_marking_order(built) -> None:
    """Pole N's common and throws (N1, N2, N4) bind to the symbol's pole N, never another's."""
    model = built.model
    (fn,) = (f for f in functions(model).values() if f.key[-3:] == ("Q1", "fn", "co"))
    spec = function_spec(model, build_indexes(model), fn, {})
    bound = {p.name: throw_port(spec, p) for p in spec.ports if p.throw is not None}
    assert bound == {
        f"{n}{t}": f"{n}.{s}"
        for n in (1, 2, 3)
        for t, s in (("1", "com"), ("2", "nc"), ("4", "no"))
    }
