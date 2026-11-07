"""A series of bare pins writes the records `d.detail.wire` wrote (API-022 A7), at any position (W2)."""

from typing import Any

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, design

from fransys_model.vocab import Conductor, WireFacet, WireRowHint

_ROWS = "BK BK BK BU RD BU BU BU BU"
# Recorded from main (detail.wire at 7257c3f06) before the call was deleted: (record, ends, colours, gauge).
_OLD = {
    "pair": [("facet", "H1.1-J1.1", "BK", "0.75"), ("wire", "H1.1-J1.1", None, None)],
    "chain_size": [
        ("hint", "H1.1-H2.1", _ROWS, "0.75"),
        ("hint", "H1.1-J1.1", _ROWS, "0.75"),
        ("wire", "H1.1-H2.1", None, None),
        ("wire", "H1.1-J1.1", None, None),
    ],
    "bare": [("hint", "H1.2-J1.2", _ROWS, "None"), ("wire", "H1.2-J1.2", None, None)],
}
_CALLS = {
    "pair": ((("J1", "1"), ("H1", "1")), ("BK", 0.75)),
    "chain_size": ((("J1", "1"), ("H1", "1"), ("H2", "1")), 0.75),
    "bare": ((("J1", "2"), ("H1", "2")), None),
}


def _devices() -> tuple[Design, Any, Any, Any]:
    d = design(fransys_parts.load("demo_parts"))
    return d, d.device("J1", "DEMO-CONN-2P"), d.device("H1", "DEMO-LAMP-24"), d.device("H2", "DEMO-LAMP-24")


def _ends(key: tuple[str, ...]) -> str:
    return "-".join(f"{end.split('/')[0][2:]}.{end.rsplit(':', 1)[1]}" for end in key[1:3])


def _records(d: Design) -> list[tuple[str, str, str | None, str | None]]:
    found = []
    for r in d._engine._design._draft._records.values():
        if isinstance(r, Conductor):
            found.append(("wire", _ends(r.key), None, None))
        elif isinstance(r, WireFacet):
            found.append(("facet", _ends(r.key), r.colour, str(r.gauge_mm2)))
        elif isinstance(r, WireRowHint):
            found.append(("hint", _ends(r.key), " ".join(s.colour for s in r.rows.values()), str(r.gauge_mm2)))
    return sorted(found, key=repr)


@pytest.mark.parametrize("case", sorted(_OLD))
def test_a_pin_only_series_writes_the_records_detail_wire_wrote(case: str) -> None:
    d, *devices = _devices()
    pins, wire = _CALLS[case]
    by_name = {device._label: device for device in devices}
    d.series(*(by_name[name][pin] for name, pin in pins), wire=wire)
    assert _records(d) == _OLD[case]


def test_a_pin_in_the_middle_is_a_node_both_hops_land_on() -> None:
    d, j, h, g = _devices()
    d.series(j["1"], h["1"], g["1"], wire=0.75)
    assert {r[1] for r in _records(d) if r[0] == "wire"} == {"H1.1-J1.1", "H1.1-H2.1"}


def test_a_middle_pin_tuple_of_the_wrong_width_is_refused_with_the_count() -> None:
    d, j, h, g = _devices()
    with pytest.raises(AuthorError, match=r"leaves with 1 pole .* takes 2 poles"):
        d.series(j["1"], (h["1"], h["2"]), g["1"], wire=0.75)


def test_a_wire_carries_the_function_block_it_was_written_in() -> None:
    """model-0442: `Conductor.block` is the `d.function` block of the call, none outside one."""
    d, j1, h1, h2 = _devices()
    with d.function("B", "Load") as block:
        d.series(j1["1"], h1.lamp["1"], wire=0.75)
    d.series(j1["2"], h2.lamp["1"], wire=0.75)
    blocks = {c.block for c in d.draft().records() if isinstance(c, Conductor) and c.kind.value == "wire"}
    assert blocks == {block.id, None}
