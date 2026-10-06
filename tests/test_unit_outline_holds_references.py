"""S20 M10: a unit's outline holds the link markers of its pins, and its title stays above it.

The fixture is `test_dd_boundary_draw._build_pass_through`: connector `x1` is the boundary pin of
nested unit `n` and of its parent `a`, wired out to a top-level item. Its pin 1 carries a vertical
off-stub box (M1) above the black box. Before M10 the outline's top edge stood 1 grid above the
black box's own labels, so the stub's box stood on the edge and above it; the owner: "increase the
heigh of the outline to encapsulate the refrence". Now the outline's top edge passes the box, and
the title, which stays on the outline, stands above that edge, clear of the stub.
"""

import importlib.util
from pathlib import Path

import pytest

from fransys_model.layout import Label, LinkMarker, Outline, layout_of

_SOURCE = Path(__file__).resolve().parent / "test_dd_boundary_draw.py"
_spec = importlib.util.spec_from_file_location("_boundary_draw_for_outlines", _SOURCE)
assert _spec is not None
assert _spec.loader is not None
_boundary_draw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_boundary_draw)


@pytest.fixture(scope="module")
def model():
    return _boundary_draw._build_pass_through().model


def _marker_and_outline(model):
    """The pass-through pin's off-stub markers, each with the outlines of its page."""
    pin = _boundary_draw._pin_one(model, "x1")
    outlines = list(layout_of(model, Outline).values())
    return [
        (marker, [o for o in outlines if o.page == marker.page])
        for marker in layout_of(model, LinkMarker).values()
        if marker.port == pin
    ]


def test_an_outline_holds_the_reference_box_and_its_title_stands_above_it(model) -> None:
    """The pin's marker box, with its stub, lies inside its page's outline; the title is above."""
    # UNDO: stages/outlines.py `unit_outlines`: the `texts += [_marker_reach(...)]` line keeps no
    #   member port's marker (`if marker.port in ()`), and the box stands past the outline's edge
    titles = [t for t in layout_of(model, Label).values() if t.slot == "outline_title"]
    held = 0
    for marker, outlines in _marker_and_outline(model):
        for outline in outlines:
            if not outline.x <= marker.x < outline.x + outline.width:
                continue
            held += 1
            # an N marker's box grows up from its port: `y` is the port end, `height` the length
            assert marker.vertical
            assert outline.y <= marker.y - marker.height
            assert marker.y <= outline.y + outline.height
            (title,) = (
                t for t in titles if t.page == outline.page and t.x == max(outline.x, 8)
            )  # layout-0104: a title keeps the 8 G text gap from the frame
            assert title.y + title.height <= outline.y
    assert held
