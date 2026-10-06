"""A link marker's stub through, or box on, a symbol or port that is not its own (S20 tally 8a).

Either reads as a connection to that symbol. The marker's own function (the one with a port at
`marker.at`) is exempt. A stub is `WIRE_THROUGH_SYMBOL`, a box `TEXT_OVERLAP`, both on a foreign
body's interior or a foreign port point.
"""

import dataclasses

from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import TEXT_OVERLAP, WIRE_THROUGH_SYMBOL
from fransys_layout.stages import Layout, LinkMarker, MarkerSide

# every origin is on the wiring grid (test_samples): the sample symbol's ports are 16 above and
# below its origin, its body 8 either side
_OWN = placed(1, x=104, y=104)  # ports (104, 88) N and (104, 120) S; body x 96..112, y 88..120
_ABOVE = placed(2, x=104, y=40)  # body x 96..112, y 24..56, ports (104, 24) and (104, 56)


def _marker(box: Box) -> LinkMarker:
    """The marker of the own function's N port at (104, 88), box as given."""
    return LinkMarker(
        connection=hid("conductor", 5),
        port=hid("port", 7),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=104, y=88),
        box=box,
        partner_page=2,
        lead=True,
    )


def _found(marker: LinkMarker, *functions) -> list[tuple[str, tuple]]:
    layout = Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=(),
        decisions=(),
        markers=(marker,),
        labels=(),
    )
    return [(f.code, f.subjects) for f in lint_geometry(layout, sheet=SHEET)]


def test_a_marker_clear_of_every_symbol_has_no_finding() -> None:
    assert _found(_marker(Box(x=96, y=64, width=32, height=8)), _OWN, _ABOVE) == []


def test_a_stub_through_a_foreign_body_is_a_wire_through_symbol() -> None:
    marker = _marker(Box(x=96, y=0, width=32, height=8))  # stub x 104, y 8..88 crosses _ABOVE
    found = _found(marker, _OWN, _ABOVE)
    subjects = tuple(sorted((marker.connection, marker.port, _ABOVE.function)))
    assert (WIRE_THROUGH_SYMBOL, subjects) in found


def test_a_box_on_a_foreign_body_is_a_text_overlap() -> None:
    marker = _marker(Box(x=96, y=30, width=32, height=8))
    found = _found(marker, _OWN, _ABOVE)
    assert (TEXT_OVERLAP, tuple(sorted((marker.port, _ABOVE.function)))) in found


def test_a_box_holding_a_foreign_port_point_is_a_text_overlap() -> None:
    # the box spans the foreign port at (104, 56) without reaching its body's interior
    marker = _marker(Box(x=96, y=56, width=32, height=8))
    found = _found(marker, _OWN, _ABOVE)
    assert (TEXT_OVERLAP, tuple(sorted((marker.port, _ABOVE.function)))) in found


def test_a_stub_over_a_foreign_port_point_alone_is_a_wire_through_symbol() -> None:
    # the stub x 104, y 72..88 ends on the foreign port (104, 72) and only touches its body
    near = placed(3, x=104, y=56)  # body x 96..112, y 40..72, ports (104, 40) and (104, 72)
    marker = _marker(Box(x=96, y=64, width=32, height=8))
    found = _found(marker, _OWN, near)
    subjects = tuple(sorted((marker.connection, marker.port, near.function)))
    assert (WIRE_THROUGH_SYMBOL, subjects) in found


def test_a_stub_through_its_own_body_is_no_finding() -> None:
    # the marker stands at the S port (104, 120); its stub runs up through the own body
    marker = dataclasses.replace(
        _marker(Box(x=96, y=64, width=32, height=8)), at=Point(x=104, y=120)
    )
    assert [f for f in _found(marker, _OWN, _ABOVE) if f[0] == WIRE_THROUGH_SYMBOL] == []


def test_a_box_on_its_own_function_is_no_finding() -> None:
    marker = _marker(Box(x=96, y=84, width=32, height=8))  # over its own body's top edge
    assert _found(marker, _OWN, _ABOVE) == []
