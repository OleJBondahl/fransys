"""Layout-0090: a unit's outline holds the link markers of its pins, and its title stays above it.

The fixture is `test_dd_boundary_draw._build_pass_through`: connector `x1` is the boundary pin of
nested unit `n` and of its parent `a`, wired out to a top-level item. Its pin 1 carries a vertical
off-stub box (M1) above the black box. Before this fix the outline's top edge stood 1 grid above the
black box's own labels, so the stub's box stood on the edge and above it; the owner: "increase the
heigh of the outline to encapsulate the refrence". Now the outline's top edge passes the box, and
the title, which stays on the outline, stands above that edge, clear of the stub.
"""

import importlib.util
from pathlib import Path

import pytest
from _core_boxes import outline_rect
from _drawn_pages import drawn_pages

_SOURCE = Path(__file__).resolve().parent / "test_dd_boundary_draw.py"
_spec = importlib.util.spec_from_file_location("_boundary_draw_for_outlines", _SOURCE)
assert _spec is not None
assert _spec.loader is not None
_boundary_draw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_boundary_draw)


@pytest.fixture(scope="module")
def model():
    return _boundary_draw._build_pass_through().model


def test_an_outline_holds_the_reference_box_and_its_title_stands_above_it(model) -> None:
    """The pin's marker box, with its stub, lies inside its page's outline; the title is above."""
    # UNDO: stages/outlines.py `unit_outlines`: the `texts += [_marker_reach(...)]` line keeps no
    #   member port's marker (`if marker.port in ()`), and the box stands past the outline's edge
    held = 0
    for drawing in drawn_pages(model).values():
        for outline in drawing.outlines:
            left, top, right, bottom = outline_rect(outline)
            for marker in drawing.markers:
                if not left <= marker.x < right:
                    continue
                held += 1
                assert marker.side in {"n", "s"}  # a vertical box
                assert top <= marker.y <= bottom
                assert outline.label is not None
                title = outline.label.box
                assert title.y + title.h <= top
    assert held
