"""`placement_chains.anchored`: a chain with one box-drawn end rides in `Facts.series`."""

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import build, house_conventions, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import Series

type _Chain = Callable[[SimpleNamespace], tuple[Any, ...]]


def _series(chain: _Chain | None) -> tuple[Series, ...]:
    """The `Facts.series` of a relay, a lamp, a PLC input and a supply, wired in one loop."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k1, h1 = d.device("K7", "DEMO-RLY-2CO-24"), d.device("H7", "DEMO-LAMP-24")
        di, psu = d.device("A7", "DEMO-PLC-DI-2"), d.device("G7", "DEMO-PSU-24")
    d.detail.wire(psu.output["+"], k1.co_1["11"], wire=(BU, 0.5))
    d.detail.wire(k1.co_1["14"], h1.lamp[1], wire=(BU, 0.5))
    d.detail.wire(h1.lamp[2], psu.output["-"], wire=(BU, 0.5))
    d.detail.wire(di.di_1["1"], k1.co_1["14"], wire=(BU, 0.5))
    if chain is not None:
        d.layout.chain(*chain(SimpleNamespace(k1=k1, h1=h1, di=di, psu=psu)))
    model = fr.build(d).model
    problem, _ = build(
        model, symbol_kit(model, LIBRARY), house_conventions(fr.settings().layout, LIBRARY), LIBRARY
    )
    return tuple(
        Series(tuple(p.split(" ")[0] for p in s.parts if isinstance(p, str)), s.anchor)
        for s in problem.facts.series
        if s.anchor
    )


@pytest.mark.rule("FLOW-DOWN")
def test_a_chain_that_ends_at_a_box_carries_the_tail_anchor() -> None:
    """Catches the box end of a chain dropped on the way to the core."""
    assert _series(lambda n: (n.k1.co_1, n.psu.output)) == (Series(("K7",), "tail"),)


@pytest.mark.rule("FLOW-DOWN")
def test_a_chain_that_starts_at_a_box_carries_no_anchor() -> None:
    """Catches a head anchor at a box pin (R502): the free build is the flow."""
    assert _series(lambda n: (n.di.di_1, n.k1.co_1, n.h1.lamp)) == ()
    assert _series(lambda n: (n.k1.co_1, n.h1.lamp, n.psu.output)) == ()


@pytest.mark.rule("FLOW-DOWN")
def test_a_chain_with_no_box_end_carries_no_anchor() -> None:
    """Catches an anchor made up for a chain of plain functions."""
    assert _series(lambda n: (n.k1.co_1, n.h1.lamp)) == ()
    assert _series(None) == ()
