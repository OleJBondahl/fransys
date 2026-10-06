"""D9 (designer ruling F7): a reference and an off stub on one port are ONE marker, one record.

The two-location cabinet draws a star reference and a stub to the other location on the same port
of `-X2:1`. Before F7 the engine drew both, the stub one box further out, and the lower marker's
stub ran through the upper one's box (`TEXT_CROSSED_BY_ROUTE`). Now the port carries one record, an
off stub (`far`, `carrier`, `facing`) whose text is the reference's list first, then the stub's
own text; its box holds every line.
"""

from collections import Counter

from layout_cabinet import build_cabinet
from samples import connection, hid

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.geometry import text_width
from fransys_layout.stages.onepage import _wired_ends
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import freeze
from fransys_model.layout import LinkMarker, StarKind, layout_of


def test_a_reference_and_an_off_stub_on_one_port_are_one_marker_reference_list_first() -> None:
    """D9 (F7): one record per (port, page); its lines are the reference's list, then the stub's."""
    # UNDO: stages/off_markers.py, the `refs={...}` argument of `OffStubs(...)` in
    #     `with_off_markers` -> `refs={}`
    #     draws the stub as a second marker on the port; the one-record count fails
    # UNDO: stages/off_markers.py:_with_off, `width = max(box.width, ...)` -> `width = box.width`
    #     leaves the box narrower than the stub line; the width check fails
    model, _ = lay_out_schematic(freeze(build_cabinet(second_location=True)))
    markers = layout_of(model, LinkMarker)
    assert set(Counter((m.port, m.page) for m in markers.values()).values()) == {1}
    (merged,) = (
        m
        for m in markers.values()
        if m.star is StarKind.OFF
        and any(o.partner == m.id and o.star is StarKind.BRANCH for o in markers.values())
    )
    *listed, stub = marker_text(model, merged).split("\n")
    assert listed
    assert all(line.startswith("#") for line in listed)  # the branches it names come first (LD3)
    assert stub == "\u2192 +C2-S2:11"  # the stub's own text, the far target, last
    profile = DEFAULT_PROFILE
    # M1: a stub on an S pin is vertical, its box the turned frame: the width is the thickness
    # (one text line each) and the height the length along the wire
    assert merged.vertical
    assert merged.width == (len(listed) + 1) * profile.text_height + 2 * profile.marker_padding
    # the stub line is the widest here, so the box grew to hold it (LD3 (c): the reference part
    # of the box is the sheet's fixed length; the stub's own measured text still grows it, D4)
    widest = max(text_width(line, height=profile.text_height) for line in (*listed, stub))
    assert text_width(stub, height=profile.text_height) == widest
    assert merged.height == widest + 2 * profile.marker_padding


def test_a_port_is_wired_on_the_pages_where_a_conductor_of_it_is_drawn() -> None:
    """layout-0053: `wired_ends` names a port on a page only where a conductor ends on it there.

    F1 stands on pages 1 and 2, F2 on page 1 only, so the conductor joining them is drawn on
    page 1 and F1's replica on page 2 has no wire. F3 and F4 stand on both pages and their
    conductor is routed on page 2.
    """
    # UNDO: stages/onepage.py:wired_ends, `pages_of[one.a.function] & pages_of[one.b.function]`
    #     -> `... | ...` lists F1's port on page 2, where it has no wire
    # UNDO: stages/onepage.py:wired_ends, `if routed_on.get(one.handle, page) == page` ->
    #     `if True` lists F3's port on page 1, where its conductor is not routed
    page1, page2 = (1, 1), (1, 2)
    joined, chosen = connection(1, 1, 2), connection(2, 3, 4)
    at_home = {(hid("function", n), page): True for n, page in [(1, page1), (1, page2), (2, page1)]}
    at_home |= {(hid("function", n), page): True for n in (3, 4) for page in (page1, page2)}
    found = _wired_ends((joined, chosen), at_home, {chosen.handle: page2})
    assert (joined.a.port, *page1) in found
    assert (joined.a.port, *page2) not in found  # a replica with no wire on its page
    assert (joined.b.port, *page1) in found
    assert (chosen.a.port, *page2) in found
    assert (chosen.a.port, *page1) not in found
