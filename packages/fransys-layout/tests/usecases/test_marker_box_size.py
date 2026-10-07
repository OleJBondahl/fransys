"""The two-location golden's markers: each across the locations, wider than a fixed reference box.

`tests/golden/cabinet_two_location_laid_out.json` (`test_usecases.py`'s `_two_location_laid_out`,
`layout_cabinet.build_cabinet(second_location=True)` on the house sheet) puts `-K1` `aux`
(`=P1`, `+C1`) and `-K2` `aux` (`=P2`, `+C2`) in two drawing sets. Since D10 a conductor between
two locations is no owner/user pair: each end is an off stub naming the far end and its
location (`test_properties_layout.py`'s
`test_a_conductor_between_two_locations_ends_in_a_stub_label_at_each_end` proves this over the
fixture; this module checks the committed golden file instead). The golden holds four such
stubs (the K1 and K2 signal ends and two more), five branch markers and two references
(layout-0052, layout-0053, layout-0057, layout-0093). Every marker is a turned box (S20 M1), so
"width" below means the side its text reads along, its height.

A separate module, not an addition to `test_usecases.py`: that module's tests are golden-vs-engine
byte comparisons (`dumps`/digest), while this one reads persisted records and checks a semantic
property of them, the same split `test_drawing_text_equality.py` already draws in this directory.

The can-fail proof below reuses `tests/golden/cabinet_narrow_laid_out.json`: its 2 pair markers
sit on two different pages but inside one drawing set (`+C1`, the narrow fixture is never given
a second location). That is the one case that tells a correct location comparison apart from a
page comparison, or from a predicate that just counts every marker: `own_page != partner_page`
is true for both pair markers, while the marker's counterpart port being in another location
than its own drawing set is false for all 9 markers. A page-vs-location confusion, or a stub
that always returns "crosses", each give the wrong count there; only the location comparison
gives 0.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from fransys_model.derive.lookups import effective_placement, item_of_port
from fransys_model.kernel import loads
from fransys_model.layout import DrawingSet, LinkMarker, Page, StarKind, layout_of
from fransys_model.vocab.enums import Aspect

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"
_TWO_LOCATION_GOLDEN = _GOLDEN_DIR / "cabinet_two_location_laid_out.json"
_NARROW_GOLDEN = _GOLDEN_DIR / "cabinet_narrow_laid_out.json"

# 4 off stubs (D10; layout-0053 merged the reference and the stub of one port, so the one at
# `-X2:1` lists the branches first) plus 5 branch and 2 reference markers: layout-0093's M12 turn
# test makes a wire that turns back round its device a reference pair (4 more than before step
# 5's 7); no owner/user pair remains.
_EXPECTED_TWO_LOCATION_MARKER_COUNT = 8
_EXPECTED_LOCATION_CROSSING_MARKER_COUNT = 4
# D9: 7 star markers (3 references and 4 branches, whose lists make them wider; two more than
# before step 5, M12's turned-back wires) plus the 2 ends of the one conductor cut by a page
# break. Not 11: the removed pair is the K1:aux:13 <-> S0:nc_2:22 wire (wire 17): K1's aux now
# stands on page 1 (layout-0049, D2: the aux stands second in =P1), so the wire is drawn on page
# 1 and is no longer cut.
_EXPECTED_NARROW_MARKER_COUNT = 8  # was 9: -S0 has -X2:1 over its pin (V4)
_EXPECTED_NARROW_PAIR_MARKER_COUNT = 2
_EXPECTED_NARROW_LOCATION_CROSSING_COUNT = 0
# LD3 (c)'s fixed reference box width for the house sheet format (`links.reference_box_width`,
# decision layout-0089): every plain pair and star reference (REF or BRANCH) on this sheet
# shares this one value, never measured from its own text.
_FIXED_REFERENCE_WIDTH_G = 42
_LINE_STUB_WIDTH_G = 43  # HL15-HL18: the OFF stub at the end of a leaving harness line


def _crosses_location(model: Model, marker: LinkMarker) -> bool:
    """Whether `marker` names a port in another location than its own page's drawing set.

    The counterpart is the off stub's `far` port, else the partner marker's port. Its item's
    effective location is compared with `DrawingSet.location`, never `marker.page` or the
    partner's page, and never `marker_text(...)` for a leading `"+"`, which would test the
    reader against itself. Both goldens' drawing sets are top-level locations, so the leaf
    location of an item and the drawing set's location are equal when they are the same.
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
    """The box's side its text reads along: its height when turned (S20 M1), else its width."""
    return marker.height if marker.vertical else marker.width


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

    Every marker but the 2 line stubs is 42 G wide.

    Exercises the identical `_crosses_location` helper and width rule the real assertion above
    uses, over a golden where the correct answer (0 crossing, width exactly 42) differs from
    what a page-vs-location confusion or a hardcoded non-42 width would give: the pair markers
    sit on different pages (asserted), so a page comparison counts both. Since LD3 (c) (decision
    layout-0089) every reference on this golden -- pair and D9 star alike, it has no off stub --
    shares the identical fixed width, so the check below covers every marker, not only the pairs.
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
    # HL15-HL18 (layout-0154): a harness line leaving the page ends in an OFF line stub, 43 G
    # long, not a reference; every other marker keeps the fixed reference width.
    line_stubs = [m for m in markers.values() if "line_stub" in str(m.key)]
    assert len(line_stubs) == 2
    assert {_along(marker) for marker in line_stubs} == {_LINE_STUB_WIDTH_G}
    assert {_along(m) for m in markers.values() if m not in line_stubs} == {
        _FIXED_REFERENCE_WIDTH_G
    }
