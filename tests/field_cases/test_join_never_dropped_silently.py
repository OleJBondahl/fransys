"""Field case: three members joined on one run, an attached terminal above one of them.

The engineering shape: the top pin of three indicator lamps, each on the top row of its column
and on one plain net, which is one run of wire (V3: a rail net would draw power symbols and no
wire). A feed-through terminal wired to the last lamp's pin attaches above that lamp, so its pin
stands a row lower than the other two. Its wire to the first lamp's pin turns back past that lamp
(S20 M12) and is no join. (The members were PLC card pins until V1 gave a module one box with its
channels as pins, ITEM-BOX; the shape needs only column ends.)

The bug (cabinet page 4): the shifted member kept its references, with no wire and no finding.
The rule (spec CONVENTIONS-V06 V6, decision layout-0099): a run whose ends cannot share a y is
aligned or gives `JOIN_UNALIGNED`, never neither.
"""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
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
            x1 = d.device("X1", "DEMO-TB-2.5")
    members = [lamp.lamp["1"] for lamp in lamps]
    for member in members[1:]:
        d.wire(members[0], member, wire=(BU, 0.5))
    if x1 is not None:
        d.wire(x1.terminal["external"], members[2], wire=(BU, 0.5))
    d.net("SIG", *members)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _references(result: fr.BuildResult) -> int:
    return len(layout_of(result.model, LinkMarker)) + len(layout_of(result.model, PowerSymbol))


def _unaligned(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(result) if f.code == "JOIN_UNALIGNED"]


def test_the_unshifted_run_is_aligned_wires() -> None:
    """The control: one aligned run, no reference and no finding."""
    result = _build(attached=False)
    assert _references(result) == 0
    assert _unaligned(result) == []


def test_a_run_with_a_shifted_member_is_aligned_or_gives_join_unaligned() -> None:
    """Either the run is wires (no reference), or `JOIN_UNALIGNED` says it was not."""
    result = _build(attached=True)
    assert _references(result) == 0 or _unaligned(result) != []
