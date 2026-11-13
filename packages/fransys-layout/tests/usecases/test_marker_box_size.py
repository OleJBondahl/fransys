"""The two-location golden's markers: each across the locations, wider than a fixed reference box.

`tests/golden/cabinet_two_location_laid_out.json` (`test_usecases.py`'s `_two_location_laid_out`,
`layout_cabinet.build_cabinet(second_location=True)` on the house sheet) puts `-K1` `aux`
"""

from pathlib import Path
from typing import TYPE_CHECKING

from fransys_model.derive import effective_placement, item_of_port
from fransys_model.kernel import loads
from fransys_model.layout import DrawingSet, LinkMarker, Page, StarKind, layout_of
from fransys_model.refdef import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"
_TWO_LOCATION_GOLDEN = _GOLDEN_DIR / "cabinet_two_location_laid_out.json"
_NARROW_GOLDEN = _GOLDEN_DIR / "cabinet_narrow_laid_out.json"

# 4 off stubs (layout-0053 merged the reference and the stub of one port, so the one at
# `-X2:1` lists the branches first) plus 5 branch and 2 reference markers: layout-0093's turn
# test makes a wire that turns back round its device a reference pair (4 more than before
# the turn change, when it was 7); no owner/user pair remains.
_EXPECTED_TWO_LOCATION_MARKER_COUNT = 4  # was 8: model-0220 draws -X2:1 as copies; layout-0224
_EXPECTED_LOCATION_CROSSING_MARKER_COUNT = 4
# 7 star markers (3 references and 4 branches, whose lists make them wider; two more than
# before the turned-back wires) plus the 2 ends of the one conductor cut by a page
# break. Not 11: the removed pair is the K1:aux:13 <-> S0:nc_2:22 wire (wire 17): K1's aux now
# stands on page 1 (layout-0049: the aux stands second in =P1), so the wire is drawn on page
# 1 and is no longer cut.
_EXPECTED_NARROW_MARKER_COUNT = 4  # was 8: model-0220 copies, and the K1:13 - S0:22 pair is a wire (layout-0224)
_EXPECTED_NARROW_PAIR_MARKER_COUNT = 2
_EXPECTED_NARROW_LOCATION_CROSSING_COUNT = 0
# The fixed reference box width for the house sheet format (`links.reference_box_width`,
# decision layout-0089): every plain pair and star reference (REF or BRANCH) on this sheet
# shares this one value, never measured from its own text.
_FIXED_REFERENCE_WIDTH_G = 47
# The OFF stub at the end of a leaving harness line; its text now lists every far
# device with its place, so the two narrow stubs measure 67 and 107 G
_LINE_STUB_WIDTHS_G = {67, 107}


def _crosses_location(model: Model, marker: LinkMarker) -> bool:
    """Whether `marker` names a port in another location than its own page's drawing set.

    The counterpart is the off stub's `far` port, else the partner marker's port. Its item's
    effective location is compared with `DrawingSet.location`, never `marker.page` or the
    """
    markers, pages = layout_of(model, LinkMarker), layout_of(model, Page)
    port = marker.far if marker.far is not None else markers[marker.partner].port
    location = effective_placement(model, item_of_port(model, port), Aspect.LOCATION)
    return location != layout_of(model, DrawingSet)[pages[marker.page].drawing_set].location


def _location_crossing_count(model: Model) -> int:
    """How many of `model`'s `layout.link_marker` records name a port in another location."""
    markers = layout_of(model, LinkMarker)
    return sum(_crosses_location(model, marker) for marker in markers.values())


def _along(marker: LinkMarker) -> int:
    """The box's long side, the one its text reads along (every stored box is a one-line text)."""
    return max(marker.width, marker.height)


def _widest_marker_width(model: Model) -> int:
    """The widest reading side among `model`'s `layout.link_marker` records."""
    return max(_along(marker) for marker in layout_of(model, LinkMarker).values())


def test_two_location_markers_are_location_prefixed_and_wider_than_a_plain_box() -> None:
    """Every marker across the locations is an off stub, wider than the fixed reference box."""
    model = loads(_TWO_LOCATION_GOLDEN.read_text(encoding="utf-8"))
    markers = layout_of(model, LinkMarker)
    assert len(markers) == _EXPECTED_TWO_LOCATION_MARKER_COUNT

    assert _location_crossing_count(model) == _EXPECTED_LOCATION_CROSSING_MARKER_COUNT
    crossing = [marker for marker in markers.values() if _crosses_location(model, marker)]
    assert {marker.star for marker in crossing} == {StarKind.OFF}
    assert not [marker for marker in markers.values() if marker.star is None]
    assert min(_along(marker) for marker in crossing) > _FIXED_REFERENCE_WIDTH_G
    assert _widest_marker_width(model) > _FIXED_REFERENCE_WIDTH_G


def test_the_location_prefix_and_width_checks_can_fail() -> None:
    """The narrow golden's 2 same-location pair markers cross no location.

    Every marker but the 2 line stubs is 47 G wide.
    Exercises the identical `_crosses_location` helper and width rule the real assertion above
    """
    model = loads(_NARROW_GOLDEN.read_text(encoding="utf-8"))
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    assert len(markers) == _EXPECTED_NARROW_MARKER_COUNT
    pairs = [marker for marker in markers.values() if marker.star is None]
    assert len(pairs) == _EXPECTED_NARROW_PAIR_MARKER_COUNT
    assert all(pages[m.page].number != pages[markers[m.partner].page].number for m in pairs)

    assert _location_crossing_count(model) == _EXPECTED_NARROW_LOCATION_CROSSING_COUNT
    assert {_along(marker) for marker in pairs} == {_FIXED_REFERENCE_WIDTH_G}
    # A harness line leaving the page ends in an OFF line stub (layout-0154),
    # 107 G long, not a reference; every other marker keeps the fixed reference width.
    line_stubs = [m for m in markers.values() if "line_stub" in str(m.key)]
    assert len(line_stubs) == 2
    assert {_along(marker) for marker in line_stubs} == _LINE_STUB_WIDTHS_G
    assert {_along(m) for m in markers.values() if m not in line_stubs} == {_FIXED_REFERENCE_WIDTH_G}
