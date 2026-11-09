"""Field case: three lamp top pins joined on one run, with a feed-through terminal attached above one of them.
The bug: the shifted member kept its references, with no wire and no finding.
Fixed by layout-0099, a run whose ends cannot share a y is aligned (no reference)."""

from typing import Any

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.layout import LinkMarker, PowerSymbol, layout_of


def _build(*, attached: bool) -> fr.BuildResult:
    """The shape above, one cabinet document."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    x1: Any = None
    with d.function("G", "Group"):
        lamps = [d.device(f"P{n}", "DEMO-LAMP-24") for n in (1, 2, 3)]
        if attached:
            x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
    members = [lamp.lamp["1"] for lamp in lamps]
    for member in members[1:]:
        d.series(members[0], member, wire=(BU, 0.5))
    if x1 is not None:
        d.series(x1[1].outer, members[2], wire=(BU, 0.5))
    for lamp in lamps[1:]:
        d.series(lamps[0].lamp["2"], lamp.lamp["2"], wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _references(result: fr.BuildResult) -> int:
    return len(layout_of(result.model, LinkMarker)) + len(layout_of(result.model, PowerSymbol))


def test_the_unshifted_run_is_aligned_wires() -> None:
    """The control: one aligned run, no reference."""
    assert _references(_build(attached=False)) == 0


def test_a_run_with_a_shifted_member_is_aligned_wires() -> None:
    """The run is wires (no reference), shifted member or not."""
    assert _references(_build(attached=True)) == 0
