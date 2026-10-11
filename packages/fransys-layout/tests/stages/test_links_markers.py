"""The marker box (turned on N and S ports) and marker text of `links`
(decision layout-0019)."""

import dataclasses

from samples import PROFILE, SHEET, built_links, connection, drawn, hid, placed, through_geometry

from fransys_layout.geometry import Box, Facing, Point, PortGeometry
from fransys_layout.stages import LinkCase, MarkerSide
from fransys_layout.stages.references import LINK_PARTNER_UNLOCATED
from fransys_layout.stages.references.digits import Digits
from fransys_layout.stages.references.marker_boxes import reference_box_width
from fransys_model.kernel import Severity

_C1 = hid("aspect_node", 900)
_C2 = hid("aspect_node", 901)
LOCATION_PATHS = frozendict({1: ((_C1, "C1"),), 2: ((_C2, "C2"),)})


def _run(
    placed_functions, *, profile=PROFILE, location_paths=LOCATION_PATHS, functions=None, units=None
):
    """Conductor 1 from port 12 of function 1 to port 21 of function 2."""
    return built_links(
        (connection(1, 1, 2),),
        (),
        placed_functions,
        functions or (drawn(1), drawn(2)),
        sheet=SHEET,
        profile=profile,
        location_paths=location_paths,
        units=units or frozendict(),
        function_units=frozendict(),
    )


def _two_pages(*, drawing_set_of_two: int = 1):
    """Function 1 on page 1 at (104, 96); function 2 at (704, 304) on the page after it."""
    return (
        placed(1, x=104, y=96, page=1),
        dataclasses.replace(
            placed(2, x=704, y=304, page=1 if drawing_set_of_two != 1 else 2),
            drawing_set=drawing_set_of_two,
        ),
    )


def _by_side(markers):
    return {marker.side: marker for marker in markers}


def _sideways(one):
    """`one` drawn with `in` on its W side and `out` on its E side, on the wiring grid."""
    geometry = dataclasses.replace(
        through_geometry(),
        ports=(
            PortGeometry(name="in", at=Point(x=-8, y=0), facing=Facing.W),
            PortGeometry(name="out", at=Point(x=8, y=0), facing=Facing.E),
        ),
    )
    return dataclasses.replace(one, geometry=geometry)


def test_a_marker_box_is_text_height_high_and_the_fixed_reference_width() -> None:
    """A severed marker's box is one line of text height and the sheet's
    fixed reference width long, never measured from its own text. On the N and S ports here it
    is turned: the line is its width, the reference width its height."""
    _, markers, _, _ = _run(_two_pages())
    by = _by_side(markers)
    width = reference_box_width(SHEET, PROFILE)
    assert len(markers) == 2
    assert all(marker.vertical for marker in markers)
    assert by[MarkerSide.OWNER].box.width == PROFILE.text_height
    assert by[MarkerSide.OWNER].box.height == width
    assert by[MarkerSide.USER].box.height == width


def test_a_marker_box_is_sized_for_its_own_sets_digits() -> None:
    """A set past 99 groups boxes its markers for three digits; a set not named keeps two."""
    # UNDO: stages/references/cuts.py `_markers`: `digits.get(end.page[0], FLOOR)` -> `FLOOR`
    placed_functions = _two_pages()
    wide = built_links(
        (connection(1, 1, 2),),
        (),
        placed_functions,
        (drawn(1), drawn(2)),
        sheet=SHEET,
        profile=PROFILE,
        location_paths=LOCATION_PATHS,
        units=frozendict(),
        function_units=frozendict(),
        digits=frozendict({1: Digits(3, 2)}),
    )[1]
    three = reference_box_width(SHEET, PROFILE, digits=Digits(3, 2))
    assert three > reference_box_width(SHEET, PROFILE)
    assert len(wide) == 2  # turned: the length is the height
    assert {marker.box.height for marker in wide} == {three}
    _, two, _, _ = _run(placed_functions)
    assert len(two) == 2
    assert {marker.box.height for marker in two} == {reference_box_width(SHEET, PROFILE)}


def test_a_marker_on_a_south_port_hangs_below_it_centred() -> None:
    """Owner: port 12 is `out`, facing S, at (104, 112). The box, turned, starts one
    stub past the port and runs away from it."""
    _, markers, _, _ = _run(_two_pages())
    box = _by_side(markers)[MarkerSide.OWNER].box
    length = reference_box_width(SHEET, PROFILE)
    assert box == Box(x=104 - 8 // 2, y=112 + 8, width=8, height=length)


def test_a_marker_on_an_east_port_grows_right_from_it() -> None:
    """Function 1's `out` faces E at (112, 96): the left edge is one stub past the port."""
    first, second = _two_pages()
    _, markers, _, _ = _run((_sideways(first), _sideways(second)))
    box = _by_side(markers)[MarkerSide.OWNER].box
    assert box == Box(x=112 + 8, y=96 - 4, width=box.width, height=8)


# --- box width: fixed per sheet, never measured ------------------------------


# --- nested locations: the nearest common ancestor ---------------------

_ER = hid("aspect_node", 800)
_ER_C1 = hid("aspect_node", 801)
_ER_FLD = hid("aspect_node", 802)
_AR = hid("aspect_node", 803)
_AR_C1 = hid("aspect_node", 804)


def test_a_shared_parent_prefixes_only_the_path_below_it() -> None:
    """`+ER+C1` to `+ER+FLD`: the prefix is `+FLD`, not the shared `+ER+FLD`.
    A severed marker's box no longer measures this at all; `_tag_echo_text` does, via
    a tag echo."""
    paths = frozendict({1: ((_ER, "ER"), (_ER_C1, "C1")), 2: ((_ER, "ER"), (_ER_FLD, "FLD"))})
    _, markers, requests, _ = _run(
        _two_pages(drawing_set_of_two=2),
        location_paths=paths,
        functions=(_one_item(1), _one_item(2)),
    )
    assert markers == ()
    assert _texts(requests) == {
        hid("function", 1): "+FLDp1:5C",
        hid("function", 2): "+C1p1:1A",
    }


# --- a partner with no location --------------------------------------------------------


def test_when_every_drawing_set_has_a_location_nothing_is_reported() -> None:
    """The near-identical input that passes."""
    _, _, _, findings = _run(_two_pages(drawing_set_of_two=2))
    assert findings == ()


# --- a tag echo may cross drawing sets -------------------------------------------------
#
# A column's location is `None` when its cells mix items of two `+` nodes (columns.md 6.2), so a
# coil
# alone in a column of one location and its contact in a mixed column can be in two drawing sets.


def _one_item(number: int):
    return dataclasses.replace(drawn(number, kind="contact_no"), item=hid("item", 99))


def _texts(requests):
    return {request.subject: request.text for request in requests}


def test_a_tag_echo_across_two_drawing_sets_cites_the_partners_location() -> None:
    """Written as `_tag_echo_text` writes it: `+<label>p<page>:<col><row>` in each function's
    texts."""
    decisions, markers, requests, findings = _run(
        _two_pages(drawing_set_of_two=2), functions=(_one_item(1), _one_item(2))
    )
    assert [d.case for d in decisions] == [LinkCase.TAG_ECHO]
    assert markers == ()
    assert _texts(requests) == {
        hid("function", 1): "+C2p1:5C",
        hid("function", 2): "+C1p1:1A",
    }
    assert findings == ()


def test_a_tag_echo_into_an_unlocated_drawing_set_is_written_bare_and_reported() -> None:
    """Set 2 has no label: the set is named for the coil (`p2.1:5C`), the warning at set 2's
    port, and no raise."""
    _, _, requests, findings = _run(
        _two_pages(drawing_set_of_two=2),
        location_paths=frozendict({1: ((_C1, "C1"),)}),
        functions=(_one_item(1), _one_item(2)),
    )
    assert _texts(requests) == {
        hid("function", 1): "p2.1:5C",
        hid("function", 2): "+C1p1:1A",
    }
    assert [(f.code, f.severity, f.subjects) for f in findings] == [
        (LINK_PARTNER_UNLOCATED, Severity.WARNING, (hid("port", 21),))
    ]


def test_the_texts_of_one_tag_are_ordered_by_drawing_set_then_page_then_column() -> None:
    """Coil 1 has a contact on page 2 of its own set and one on page 1 of set 2: own set first."""
    coil, elsewhere, later = (_one_item(n) for n in (1, 2, 3))
    functions = (
        placed(1, x=104, y=96, page=1),
        dataclasses.replace(placed(2, x=704, y=304, page=1), drawing_set=2),
        placed(3, x=704, y=304, page=2),
    )
    _, _, requests, _ = built_links(
        (connection(1, 1, 2), connection(2, 1, 3)),
        (),
        functions,
        (coil, elsewhere, later),
        sheet=SHEET,
        profile=PROFILE,
        location_paths=LOCATION_PATHS,
        units=frozendict(),
        function_units=frozendict(),
    )
    assert _texts(requests)[hid("function", 1)] == "p2:5C +C2p1:5C"


def test_a_marker_on_a_north_port_stands_above_it_centred() -> None:
    """User: port 21 is `in`, facing N, at (704, 288). The box, turned, ends one stub
    short of the port and runs away from it."""
    _, markers, _, _ = _run(_two_pages())
    box = _by_side(markers)[MarkerSide.USER].box
    length = reference_box_width(SHEET, PROFILE)
    assert box == Box(x=704 - 8 // 2, y=288 - 8 - length, width=8, height=length)
