"""Field case: a `layout.chain` may name a box-drawn function at its head or tail.

The engineering shape: a PLC input channel (or a power supply output) is wired to a relay
contact, which drives a lamp. The author advises the drawing with a chain that starts at the
channel, or ends at the supply output, because that is the path the current takes.

The bug: the build raised `HintError: a chain names a function that is not drawn`, while the same
circuit without the chain wrote. A box-drawn function stands in its device's box, not in a chain
column of its own.
The rule (decision layout-0181, owner 2026-09-23: layout continues a chain through any function):
a chain may name a box-drawn function at its head or tail. The box stays where it is drawn and
anchors the chain: the neighbour is entered at the pin wired to the box. In the middle of a chain
a box-drawn function raises an `AuthorError` (0184) that says where box-drawn functions may stand.
"""

from collections.abc import Callable
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_layout.geometry import Orientation
from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items

if TYPE_CHECKING:
    from pathlib import Path

type _Chain = Callable[[SimpleNamespace], tuple[Any, ...]]


def _build(chain: _Chain | None, *, box_feeds: str, out: Path | None = None) -> Any:
    """The build of a relay, a lamp, a PLC input and a supply, a PLC input or `+` at `box_feeds`.

    The channel (or the supply `+`) lands on pin `box_feeds` of the contact, the lamp on the other.
    """
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Chain", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    wire = (BU, 0.5)
    with d.function("G", "Group"):
        k1 = d.device("K7", "DEMO-RLY-2CO-24")
        h1 = d.device("H7", "DEMO-LAMP-24")
        di = d.device("A7", "DEMO-PLC-DI-2")
        psu = d.device("G7", "DEMO-PSU-24")
    other = "14" if box_feeds == "11" else "11"
    feed = di.di_1["1"] if box_feeds == "14" else psu.output["+"]
    d.detail.wire(feed, k1.co_1[box_feeds], wire=wire)
    d.detail.wire(k1.co_1[other], h1.lamp[1], wire=wire)
    d.detail.wire(h1.lamp[2], psu.output["-"], wire=wire)
    if chain is not None:
        d.layout.chain(*chain(SimpleNamespace(k1=k1, h1=h1, di=di, psu=psu)))
    result = fr.build(d, cabinet_document(cab))
    assert [f for f in result.findings if f.severity.name == "ERROR"] == []
    if out is not None:
        fr.write(result, out)
    return result


def _contact_turn(chain: _Chain | None, *, box_feeds: str, out: Path | None = None) -> Orientation:
    """The orientation of relay K7's contact."""
    model = _build(chain, box_feeds=box_feeds, out=out).model
    (turn,) = (
        p.orientation
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].name == "co_1"
        and items(model)[functions(model)[p.function].item].tag == "K7"
    )
    return turn


def test_a_chain_may_start_at_a_plc_channel(tmp_path: Path) -> None:
    """The channel lands on pin 14, so the contact is entered at 14: it is drawn turned."""
    free = _contact_turn(None, box_feeds="14")
    chained = _contact_turn(
        lambda n: (n.di.di_1, n.k1.co_1, n.h1.lamp), box_feeds="14", out=tmp_path
    )
    assert free is Orientation.R0
    assert chained is Orientation.MR180


def test_the_box_of_a_chains_head_keeps_the_column_it_shares_with_its_other_channel() -> None:
    """The module's second channel feeds relay K8: the module stays in discovery's column of K8.

    A box left out of discovery would stand alone in a column of its own at the left.
    """
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Chain", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    wire = (BU, 0.5)
    with d.function("G", "Group"):
        k1, k2 = d.device("K7", "DEMO-RLY-2CO-24"), d.device("K8", "DEMO-RLY-2CO-24")
        h1, di = d.device("H7", "DEMO-LAMP-24"), d.device("A7", "DEMO-PLC-DI-2")
        psu = d.device("G7", "DEMO-PSU-24")
    d.detail.wire(di.di_1["1"], k1.co_1["14"], wire=wire)
    d.detail.wire(k1.co_1["11"], h1.lamp[1], wire=wire)
    d.detail.wire(h1.lamp[2], psu.output["-"], wire=wire)
    d.detail.wire(di.di_2["2"], k2.co_1["14"], wire=wire)
    d.detail.wire(k2.co_1["11"], psu.output["+"], wire=wire)
    d.layout.chain(di.di_1, k1.co_1, h1.lamp)
    model = fr.build(d, cabinet_document(cab)).model
    at = {
        (items(model)[functions(model)[p.function].item].tag, functions(model)[p.function].name): p
        for p in layout_of(model, SymbolPlacement).values()
    }
    module, relay = at["A7", "di_1"], at["K8", "co_1"]
    assert abs(module.x - relay.x) <= 32  # One column
    assert module.y > relay.y


def test_a_chain_may_end_at_a_supply_output(tmp_path: Path) -> None:
    """The supply lands on pin 11 and ends the chain: the contact leaves at 11, drawn turned."""
    free = _contact_turn(None, box_feeds="11")
    chained = _contact_turn(lambda n: (n.k1.co_1, n.psu.output), box_feeds="11", out=tmp_path)
    assert free is Orientation.R0
    assert chained is Orientation.MR180


def test_a_longer_chain_may_end_at_a_supply_output(tmp_path: Path) -> None:
    chained = _contact_turn(
        lambda n: (n.k1.co_1, n.h1.lamp, n.psu.output), box_feeds="14", out=tmp_path
    )
    assert chained is Orientation.R0  # entered at 11 (N), the supply closes the path below


def test_a_chain_may_not_pass_through_a_box_drawn_function() -> None:
    with pytest.raises(fr.AuthorError, match="only at its head or its tail"):
        _contact_turn(lambda n: (n.k1.co_1, n.di.di_1, n.h1.lamp), box_feeds="14")
