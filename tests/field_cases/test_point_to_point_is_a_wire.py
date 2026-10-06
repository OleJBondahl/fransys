"""Field case: a PSU output wired to one load pin is a wire, not a supply bar.

The engineering shape: a 24 V DC supply with rails 24 V and 0 V. One PSU feeds one lamp over a
single conductor per output: its `+` to the lamp's pin 1 and its `-` to pin 2, each a net of two
ports. A second PSU beside it feeds two lamps from the same rails, so each of its nets has three
ports and distributes.

The bug: a two-port net on a 24 V potential drew a supply bar and a ground symbol at each end,
where the owner reads a point-to-point connection as a wire.

The rule (decision model-0117, amended; CONVENTIONS-V06 V3): `power_kind` is NONE for a physical
net of exactly two ports, whatever its potential, and a net of three or more ports keeps its
kind and its symbols. The two-port net keeps its potential for the voltage check.
"""

from collections import Counter
from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BU

from fransys_model.layout import LinkMarker, PowerSymbol, layout_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from pathlib import Path

_LAMPS = 12  # enough lamps that the sheet is cut and a rail end becomes a symbol
_WIRE = (BU, 0.5)


def _build(tmp_path: Path, *, potential: bool = True) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        solo = d.device("T1", "DEMO-PSU-24")
        lone = d.device("P0", "DEMO-LAMP-24")
        feed = d.device("T2", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(1, _LAMPS + 1)]
    # one supply per PSU: the solo pair's rails are named apart, the voltages stay 24 V and 0 V
    d.dc_supply("FEED", feed)
    d.wire(solo.output["+"], lone["1"], wire=_WIRE)
    d.wire(solo.output["-"], lone["2"], wire=_WIRE)
    if potential:
        d.dc_supply("SOLO", solo, names=("SOLO_24", "SOLO_0"))
    else:  # the 24 V net plain, no potential; its 0 V net as plain
        d.net("SOLO_24", solo.output["+"], lone["1"], kind=fr.GENERIC)
        d.net("SOLO_0", solo.output["-"], lone["2"], kind=fr.GENERIC)
    for pin, source in (("1", feed.output["+"]), ("2", feed.output["-"])):
        for lamp in lamps:
            d.wire(source, lamp[pin], wire=_WIRE)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _tag(key: tuple) -> str:
    """The device tag of a port key: its item part without the function block's `G/`."""
    return key[-5].rpartition("/")[2]


def _tags(model, items) -> set[str]:
    table = ports(model)
    return {_tag(table[one.port].key) for one in items}


def _solo_markers(model) -> Counter:
    """The link markers at the solo pair's pins, by `(tag, pin)`: a cut pair has one each."""
    table = ports(model)
    return Counter(
        (_tag(table[m.port].key), table[m.port].key[-1])
        for m in layout_of(model, LinkMarker).values()
        if _tag(table[m.port].key) in {"T1", "P0"}
    )


_PAIRS = {("T1", "+"): 1, ("T1", "-"): 1, ("P0", "1"): 1, ("P0", "2"): 1}


def test_a_two_port_24v_net_draws_no_bar_and_the_distributing_net_draws_bars(tmp_path) -> None:
    model = _build(tmp_path).model
    barred = _tags(model, layout_of(model, PowerSymbol).values())
    assert barred.isdisjoint({"T1", "P0"})
    assert {"T2", "P1", f"P{_LAMPS}"} <= barred
    assert _solo_markers(model) == _PAIRS  # the cut shows one reference pair per net


def test_a_cut_two_port_plain_net_builds_with_one_marker_pair(tmp_path) -> None:
    """The 24 V net plain, no potential: a declared net and its own wire make one cut, not two."""
    model = _build(tmp_path, potential=False).model
    assert _solo_markers(model) == _PAIRS
