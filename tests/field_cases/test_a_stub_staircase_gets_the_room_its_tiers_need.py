"""Field case: a cluster of stubs in a page's first row needed more room above than the page kept.
The bug: the staircase of stubs did not fit under the page edge, so it was dropped and the stubs printed over each other.
Fixed by layout-0257: the room above the first row and below the last grows one tier per further cell, up to two."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import cabinet_document

from fransys_layout.geometry import G_PER_MODULE, Box, boxes_meet
from fransys_model.layout import LinkMarker, Side, layout_of

_CABLES = 4
_VALVE = (("coil", "A1"), ("coil", "A2"), ("co_1", "11"), ("co_1", "14"))
_CONTENT = Box(x=16, y=16, width=1280, height=822)


class _Cabinet(NamedTuple):
    F8: Any
    K1: Any
    K3: Any
    K5: Any
    K7: Any
    DI: Any
    XF: Any


class _Top(NamedTuple):
    T: Any


@fr.unit("demo-inner", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _inner(d: fr.Design) -> _Cabinet:
    d.layout.profile(hide_unused_pins=True)
    relays = [d.device(f"K{k}", "DEMO-RLY-4CO-24", interface=("co_1",)) for k in (1, 3, 5, 7)]
    f8 = d.device("F8", "DEMO-MCB-2P", interface=("pole_1",))
    xf = d.terminal_strip("XF", "DEMO-TB-2.5", 7, interface=(4, 5, 6, 7), bridged=True)
    d.series(f8.pole_1["1"], xf[1], wire=("BK", 0.75))
    return _Cabinet(
        f8,
        relays[0],
        relays[1],
        relays[2],
        relays[3],
        d.device("DI", "DEMO-PLC-DI-16", interface=tuple(f"di_{9 + 2 * n}" for n in range(4))),
        xf,
    )


@fr.unit("demo-outer", revision=1, interface_version=1, date="2026-01-01", text="r", by="XX")
def _outer(d: fr.Design) -> _Top:
    d.layout.profile(hide_unused_pins=True)
    cab = d.add(_inner, "CSC")
    for n in range(_CABLES):
        pins = (
            cab.F8.pole_1["2"],
            getattr(cab, f"K{2 * n + 1}").co_1["14"],
            getattr(cab.DI, f"di_{9 + 2 * n}")[str(9 + 2 * n)],
            cab.XF[4 + n],
        )
        with d.function(f"CV{n + 1}", f"Valve {n + 1}"):
            valve = d.device(f"M{n + 1}", "DEMO-RLY-4CO-24")
            cable = d.cable(f"W{n + 1:04d}", "DEMO-CBL-4G1.5")
            for core, (pin, (name, port)) in enumerate(zip(pins, _VALVE, strict=True), start=1):
                cable.core(core, pin, getattr(valve, name)[port])
    return _Top(d.device("T", "DEMO-RLY-4CO-24"))


@pytest.fixture(scope="module")
def stubs() -> list[tuple[Any, Box]]:
    """Each leaving-line stub as `(page, box)`, the box as drawn."""
    d = fr.design("demo_parts")
    d.add(_outer, "U1")
    built = fr.build(d, cabinet_document("demo-outer"))
    found = []
    for m in layout_of(built.model, LinkMarker).values():
        if m.pairs[0].carrier is None:
            continue
        y = m.y - G_PER_MODULE - m.height if m.facing is Side.N else m.y + G_PER_MODULE
        x = m.x - m.width // 2 if m.box_x is None else m.box_x
        found.append((m.page, Box(x=x, y=y, width=m.width, height=m.height)))
    return found


def test_a_page_has_three_or_more_stubs_in_a_cluster(stubs: list[tuple[Any, Box]]) -> None:
    per_page = [sum(1 for p, _ in stubs if p == page) for page in {p for p, _ in stubs}]
    assert max(per_page) >= 3


def test_no_two_stub_boxes_of_a_page_meet(stubs: list[tuple[Any, Box]]) -> None:
    meeting = [(a, b) for n, (page, a) in enumerate(stubs) for other, b in stubs[n + 1 :] if page == other and boxes_meet(a, b, closed=False)]
    assert meeting == []


def test_every_stub_box_stands_in_the_content_box(stubs: list[tuple[Any, Box]]) -> None:
    out = [
        box
        for _, box in stubs
        if not (
            _CONTENT.x <= box.x
            and _CONTENT.y <= box.y
            and box.x + box.width <= _CONTENT.x + _CONTENT.width
            and box.y + box.height <= _CONTENT.y + _CONTENT.height
        )
    ]
    assert out == []
