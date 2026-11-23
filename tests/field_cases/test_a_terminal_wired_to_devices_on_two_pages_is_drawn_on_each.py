"""The relay bank fed from strip X1: the builder the placement corpus (w04) and the fransys_el strip tests share.
The 120 mm sheet door is deleted (R1461, R1458); the 58-relay test on the default A3 sheet is KI-003's closed witness (R1462)."""

import itertools
from contextlib import nullcontext
from functools import cache
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document

from fransys_model.kernel import id_namespace
from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import ports

_COUNT = 16
_W04 = 58  # on the default A3 sheet the bank spans two pages from here (KI-003)


class _Io(NamedTuple):
    feed: fr.TerminalStrip


def _star_end(feed: Any, i: int, relays: list[Any]) -> Any:
    """What relay K`i + 1`'s A1 wires to: X1:1 takes the first two relays inner and the last two outer (a twin point takes 2, R1266)."""
    if i < 2:
        return feed[1]
    if i >= len(relays) - 2:
        return feed[1].outer
    return feed[3] if i == 2 else relays[i - 1].coil["A1"]  # K3 takes X1:3; the rest chain A1 to A1 (device pins have no limit)


def _bank(*, chained: bool, count: int = _COUNT):
    @fr.unit("demo-two-pages", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        feed = u.terminal_strip("X1", "DEMO-TB-2.5" if chained else "DEMO-TB-2.5-TWIN", 4, interface=True)
        with u.function("R", "Relays"):
            relays = [u.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(count)]
        ends = {}  # chained: a terminal point takes one conductor (R1266), so each terminal's relays chain coil to coil
        for i, relay in enumerate(relays):
            terminal = ends.get(i % 4, feed[1 + i % 4].inner) if chained else _star_end(feed, i, relays)
            u.series(terminal, relay.coil["A1"], wire=("WH", 0.75))
            ends[i % 4] = relay.coil["A1"]
        if not chained:  # the last inner relay also chains A1 to A1, so it stands with the chained ones on the second page
            u.series(relays[-3].coil["A1"], relays[-2].coil["A1"], wire=("WH", 0.75))
            u.series(feed[2], relays[2].coil["A2"], wire=("WH", 0.75))
            u.series(feed[2].outer, relays[-1].coil["A2"], wire=("WH", 0.75))
            others = (*relays[:2], *relays[3:-1])
            zero = u.terminal_strip("X0", "DEMO-TB-2.5", len(others)).run("0V", len(others), bridged=True)
            for n, r in enumerate(others, 1):
                u.series(r.coil["A2"], zero[n].inner, wire=("BU", 0.75))
        if chained:
            for a, b in itertools.pairwise(relays):
                u.series(a.coil["A2"], b.coil["A2"], wire=("BU", 0.75))
        return _Io(feed)

    return bank


@cache
def _model(*, chained: bool = False) -> Any:
    d = fr.design("demo_parts")
    d.add(_bank(chained=chained), "U1")
    document = unit_document("demo-two-pages")
    return fr.build(d, document).model


def test_every_drawn_id_is_a_model_id() -> None:
    """Guards stage-only handles from leaking into records."""
    model = _model()
    known_ports = set(ports(model))
    assert {m.port for m in layout_of(model, LinkMarker).values()} <= known_ports


def test_a_58_relay_bank_on_the_default_sheet_draws_every_connection() -> None:
    d = fr.design("demo_parts")
    d.add(_bank(chained=False, count=_W04), "U1")
    built = fr.build(d, unit_document("demo-two-pages"))
    assert [f for f in built.findings if f.severity.name == "ERROR"] == []
    assert [f for f in built.findings if f.code in {"CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END"}] == []


@pytest.mark.rule("BUNDLE-LANE-END")
@pytest.mark.parametrize("salt", ["-", "a", "b", "c", "d", "e"])
def test_an_arrow_pair_with_an_end_that_stands_nowhere_leaves_no_lane_dangling(salt: str) -> None:
    """R1488, R1639: the arrow at -U1-K10/in keeps its half box and a grid under its lane, so it finds a stand (KI-564)."""

    d = fr.design("demo_parts")
    d.add(_bank(chained=False), "U1")
    with id_namespace(salt) if salt != "-" else nullcontext():
        found = [f.code for f in fr.build(d, unit_document("demo-two-pages")).findings if f.code in {"DANGLING_WIRE_END", "MARKER_UNPLACED"}]
    assert found == []


def test_a_row_whose_legs_pass_the_page_when_placed_is_cut_again() -> None:
    """R1618: the first cut cannot see the legs; the placer's WIDER_THAN_PAGE sends the cut round once more, so no row stays wider."""
    d = fr.design("demo_parts")
    d.add(_bank(chained=False), "U1")
    assert [f.code for f in fr.build(d, unit_document("demo-two-pages")).findings if f.code == "WIDER_THAN_PAGE"] == []
