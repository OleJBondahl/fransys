"""Bottom headroom tightens `PAGE_OVERFULL` alone (layout-0035), on top of the bottom
reference band every page keeps."""

import dataclasses

from routing import route
from samples import PROFILE, SHEET, column, drawn, hid, page_plan, placed

from fransys_layout.geometry import translate
from fransys_layout.lint import lint_geometry
from fransys_layout.stages import Connection, Layout, PortRef, Role, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import PAGE_OVERFULL, _reference_band


def _keepout(one):
    return translate(one.geometry.keepout, dx=one.at.x, dy=one.at.y)


def _one_column(*, bottom_headroom_lanes=None, sheet=SHEET):
    options = (
        {} if bottom_headroom_lanes is None else {"bottom_headroom_lanes": bottom_headroom_lanes}
    )
    return place(
        page_plan(("a",)),
        (column("a", (1,)),),
        (drawn(1),),
        PageStacking(profile=PROFILE, sheet=sheet, **options),
    )


# Every page keeps a band along the content box's bottom as well as its top, the same on
# every page. The lone 32 G cell spans one band to one band + 32 G (the columns start below the
# top band), so the smallest content box that holds it has a band below it too.
_BAND = _reference_band(SHEET, PROFILE)
_FITS = _BAND + 32 + _BAND


def test_bottom_headroom_is_part_of_the_page_height_a_column_that_fits_without_it_may_not() -> None:
    """The two bands only fit with no bottom lanes (the least box); one lane overfulls the cell."""
    sheet = dataclasses.replace(SHEET, content_height=_FITS)
    _, findings = _one_column(sheet=sheet)
    assert findings == ()
    _, findings = _one_column(bottom_headroom_lanes=1, sheet=sheet)
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert findings[0].subjects == (hid("function", 1),)


# ---- the finding, kept as a real test ----

_LAST = 864  # the largest grid origin whose keep-out box (to 880) fits the 886 G content box


def _south_ports_joined(*, flush_y: int):
    """Two functions side by side, their south-facing (`out`) ports joined, both at `flush_y`."""
    cells = (placed(1, x=104, y=flush_y), placed(2, x=264, y=flush_y))
    joined = Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=hid("port", 12)),
        b=PortRef(function=hid("function", 2), port=hid("port", 22)),
    )
    routes, route_findings = route(
        (joined,), (), cells, (drawn(1), drawn(2)), reserved=(), profile=PROFILE, sheet=SHEET
    )
    layout = Layout(pages=(), placed=cells, routes=routes, decisions=(), markers=(), labels=())
    return route_findings, lint_geometry(layout, sheet=SHEET)
