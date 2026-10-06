"""`TEXT_OVERLAP`: two texts, or a text over a foreign symbol body (lint/_texts.py, layout-0047).

Moved from the designer's test-side `text_overlaps` helper (`tests/engines/test_review_metrics.py`
before F7) into the lint, next to `TEXT_CROSSED_BY_ROUTE`; these cases are its unit tests, run
through `lint_geometry` as `test_text_crossed.py` runs its own.
"""

import dataclasses

import pytest
from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.lint import lint_geometry
from fransys_layout.lint.codes import TEXT_OVERLAP
from fransys_layout.stages import LabelKind, Layout, LinkMarker, MarkerSide, PlacedLabel


def _label(subject: int, box: Box, *, page: int = 1) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", subject),
        slot="tag",
        drawing_set=1,
        page=page,
        box=box,
    )


def _marker(port: int, box: Box, *, lead: bool = True, page: int = 1) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 5),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=page,
        at=Point(x=box.x, y=box.y),
        box=box,
        partner_page=2,
        lead=lead,
    )


def _layout(*, functions=(), labels=(), markers=()) -> Layout:
    return Layout(
        pages=(page_plan(("a",)),),
        placed=functions,
        routes=(),
        decisions=(),
        markers=markers,
        labels=labels,
    )


def _found(layout: Layout) -> list[tuple[str, tuple]]:
    return [
        (f.code, f.subjects) for f in lint_geometry(layout, sheet=SHEET) if f.code == TEXT_OVERLAP
    ]


_BOX = Box(x=100, y=100, width=40, height=8)


# --- two texts --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        pytest.param(Box(x=120, y=104, width=40, height=8), True, id="interiors overlap"),
        pytest.param(Box(x=140, y=100, width=40, height=8), False, id="side by side, touching"),
        pytest.param(Box(x=100, y=108, width=40, height=8), False, id="stacked, touching"),
        pytest.param(Box(x=100, y=100, width=40, height=8), True, id="the same box twice"),
        pytest.param(Box(x=300, y=100, width=40, height=8), False, id="far apart"),
    ],
)
def test_two_labels_overlap_only_by_their_interior(other: Box, *, expected: bool) -> None:
    """Both axes strict, as for every other overlap check: touching edges do not fire."""
    found = _found(_layout(labels=(_label(1, _BOX), _label(2, other))))
    assert bool(found) is expected
    if expected:
        assert found == [(TEXT_OVERLAP, (hid("function", 1), hid("function", 2)))]


def test_a_label_over_a_marker_box_and_two_marker_boxes_overlap_too() -> None:
    """Every kind pair counts: label with marker, marker with marker."""
    over = Box(x=110, y=102, width=40, height=8)
    assert _found(_layout(labels=(_label(1, _BOX),), markers=(_marker(11, over),))) == [
        (TEXT_OVERLAP, tuple(sorted((hid("function", 1), hid("port", 11)))))
    ]
    two = _layout(markers=(_marker(11, _BOX), _marker(21, over)))
    assert _found(two) == [(TEXT_OVERLAP, tuple(sorted((hid("port", 11), hid("port", 21)))))]


def test_a_non_lead_marker_shares_its_leads_box_and_is_no_text_of_its_own() -> None:
    """A bundle row's markers share one box: counting each would overlap the lead with itself."""
    follower = dataclasses.replace(_marker(21, _BOX), lead=False)
    lead = _marker(11, _BOX)
    assert _found(_layout(markers=(lead, follower))) == []


def test_boxes_of_two_pages_never_overlap() -> None:
    """The same box on two pages is two pages' texts."""
    layout = _layout(labels=(_label(1, _BOX), _label(2, _BOX, page=2)))
    assert _found(layout) == []


# --- a text over a symbol body ----------------------------------------------------------

# `placed(1, x=104, y=96)` bodies at x [96, 112], y [80, 112] (`through_geometry`, samples.py).
_OVER_BODY = Box(x=100, y=90, width=10, height=10)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        pytest.param(_OVER_BODY, True, id="over the body's interior"),
        pytest.param(Box(x=112, y=90, width=10, height=10), False, id="resting on the body's edge"),
        pytest.param(Box(x=200, y=90, width=10, height=10), False, id="clear of the body"),
    ],
)
def test_a_foreign_tag_over_a_body_is_through_by_its_interior_only(
    box: Box, *, expected: bool
) -> None:
    """A tag of a different function reaching the body is `TEXT_OVERLAP`; touching is not."""
    layout = _layout(functions=(placed(1, x=104, y=96),), labels=(_label(2, box),))
    found = _found(layout)
    assert bool(found) is expected
    if expected:
        assert found == [(TEXT_OVERLAP, tuple(sorted((hid("function", 1), hid("function", 2)))))]


def test_a_tag_over_its_own_symbol_does_not_fire() -> None:
    """The device's own tag, subject function 1, reaching function 1's own body: not foreign."""
    layout = _layout(functions=(placed(1, x=104, y=96),), labels=(_label(1, _OVER_BODY),))
    assert _found(layout) == []


def test_a_port_marking_reaching_its_own_body_does_not_fire_either() -> None:
    """A marker standing at a port of the function is that function's own: its box may reach it.

    Measured on the invented cabinet (`tests/engines/test_review_metrics.py`): a part's own
    port markings routinely reach its own body by D14's near edge, which is by design, not a
    defect. The owner is the function with a port at `marker.at` (`lint/_foreign.py`); a box on
    a body that is not the owner's is `test_foreign_symbol.py`'s.
    """
    own = dataclasses.replace(_marker(11, _OVER_BODY), at=Point(x=104, y=80))  # the `in` port
    layout = _layout(functions=(placed(1, x=104, y=96),), markers=(own,))
    assert _found(layout) == []
