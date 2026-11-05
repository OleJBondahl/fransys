"""Field case: a PSU output wired to one load pin is a wire, not a supply bar.
The bug: a two-port net on a 24 V potential drew a supply bar and a ground symbol at each end, where the owner reads a wire.
Fixed by model-0117 (amended), power_kind is NONE for a physical net of exactly two ports, whatever its potential."""

from collections import Counter
from typing import Any

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.layout import LinkMarker, PowerSymbol, layout_of
from fransys_model.vocab.tables import ports

_LAMPS = 12  # enough lamps that the sheet is cut and a rail end becomes a symbol
_WIRE = (BU, 0.5)


def _build(*, potential: bool = True) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        solo = d.device("T1", "DEMO-PSU-24")
        lone = d.device("P0", "DEMO-LAMP-24")
        feed = d.device("T2", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(1, _LAMPS + 1)]
    # one supply per PSU: the solo pair's rails are named apart, the voltages stay 24 V and 0 V
    d.dc_supply("FEED", feed)
    d.series(solo.output["+"], lone["1"], wire=_WIRE)
    d.series(solo.output["-"], lone["2"], wire=_WIRE)
    if potential:
        d.dc_supply("SOLO", solo, names=("SOLO_24", "SOLO_0"))
    for pin, source in (("1", feed.output["+"]), ("2", feed.output["-"])):
        for lamp in lamps:
            d.series(source, lamp[pin], wire=_WIRE)
    doc = unit_document(cab)
    return fr.build(d, doc)


def _tag(key: tuple[Any, ...]) -> Any:
    """The device tag of a port key: its item part without the function block's `G/`."""
    return key[-5].rpartition("/")[2]


def _tags(model, items) -> set[str]:
    table = ports(model)
    return {_tag(table[one.port].key) for one in items}


def _solo_markers(model) -> Counter[Any]:
    """The link markers at the solo pair's pins, by `(tag, pin)`: a cut pair has one each."""
    table = ports(model)
    return Counter(
        (_tag(table[m.port].key), table[m.port].key[-1]) for m in layout_of(model, LinkMarker).values() if _tag(table[m.port].key) in {"T1", "P0"}
    )


_PAIRS = {("T1", "+"): 1, ("T1", "-"): 1, ("P0", "1"): 1, ("P0", "2"): 1}


def test_a_two_port_24v_net_draws_no_bar_and_the_distributing_net_draws_bars() -> None:
    model = _build().model
    barred = _tags(model, layout_of(model, PowerSymbol).values())
    assert barred.isdisjoint({"T1", "P0"})
    assert {"T2", "P1", f"P{_LAMPS}"} <= barred
    assert _solo_markers(model) == _PAIRS  # the cut shows one reference pair per net


def test_a_cut_two_port_plain_net_builds_with_one_marker_pair() -> None:
    """The 24 V net plain, no potential: a declared net and its own wire make one cut, not two."""
    model = _build(potential=False).model
    assert _solo_markers(model) == _PAIRS
