"""The marker box (LD3 (c), S20 M1/M2: turned on N and S ports) and marker text of `links`
(docs/design/links.md 6.6, decision layout-0019)."""

import dataclasses

from samples import PROFILE, SHEET, built_links, connection, drawn, hid, placed, through_geometry

from fransys_layout.geometry import Box, Facing, Point, PortGeometry
from fransys_layout.stages import LinkCase, LinkMarker, MarkerSide
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
    """LD3 (c), S20 M1/M2: a severed marker's box is one line of text height and the sheet's
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
    """S4: a set past 99 groups boxes its markers for three digits; a set not named keeps two."""
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
    assert len(wide) == 2  # turned (S20 M1): the length is the height
    assert {marker.box.height for marker in wide} == {three}
    _, two, _, _ = _run(placed_functions)
    assert len(two) == 2
    assert {marker.box.height for marker in two} == {reference_box_width(SHEET, PROFILE)}


def test_the_box_width_grows_with_a_wider_sheets_frame_grid() -> None:
    """LD3 (c): the box tracks the SHEET's frame grid, never the marker's own text.

    `SHEET` (`samples.py`) has 8 columns and 6 rows, both one digit/letter wide ("8F"). A sheet
    with 99 columns needs a 2-digit widest column label ("99"), so its `reference_box_width`
    -- and every marker's box on it -- is wider, with the SAME two-port fixture and text on
    both runs (`_two_pages()` never changes, `links` builds no marker text at all): the only
    thing that varies between the two calls is the sheet's own frame grid.
    """
    wide_sheet = dataclasses.replace(SHEET, frame_columns=99)
    _, narrow_markers, _, _ = _run(_two_pages())
    _, wide_markers, _, _ = built_links(
        (connection(1, 1, 2),),
        (),
        _two_pages(),
        (drawn(1), drawn(2)),
        sheet=wide_sheet,
        profile=PROFILE,
        location_paths=LOCATION_PATHS,
        units=frozendict(),
        function_units=frozendict(),
    )
    narrow_width = reference_box_width(SHEET, PROFILE)
    wide_width = reference_box_width(wide_sheet, PROFILE)
    assert narrow_width < wide_width
    assert len(narrow_markers) == len(wide_markers) == 2
    assert {m.box.height for m in narrow_markers} == {narrow_width}  # turned: length = height
    assert {m.box.height for m in wide_markers} == {wide_width}


def test_the_box_height_and_width_follow_the_profile_text_height() -> None:
    """The near-identical input with another text height: the box grows with it. On these N and
    S ports the box is turned (S20 M1): the line height is its width, the length its height."""
    bigger = dataclasses.replace(PROFILE, text_height=16)
    (_, small), (_, large) = (_run(_two_pages(), profile=p)[:2] for p in (PROFILE, bigger))
    assert [m.box.width for m in small] == [8, 8]
    assert [m.box.width for m in large] == [16, 16]
    assert large[0].box.height > small[0].box.height


def test_the_box_grows_by_twice_the_marker_padding() -> None:
    """`marker_padding` (decision layout-0043's amendment) adds to both the width and height.

    `PROFILE.marker_padding` is 0 (`samples.py`), so every other test in this file keeps
    its unpadded box math; this test alone turns padding on, by `dataclasses.replace`.
    """
    padded = dataclasses.replace(PROFILE, marker_padding=3)
    (_, unpadded), (_, with_padding) = (
        _run(_two_pages(), profile=p)[:2] for p in (PROFILE, padded)
    )
    owner_plain = _by_side(unpadded)[MarkerSide.OWNER].box
    owner_padded = _by_side(with_padding)[MarkerSide.OWNER].box
    assert owner_padded.width == owner_plain.width + 2 * 3
    assert owner_padded.height == owner_plain.height + 2 * 3


def test_a_marker_on_a_south_port_hangs_below_it_centred() -> None:
    """Owner: port 12 is `out`, facing S, at (104, 112). The box, turned (S20 M1), starts one
    stub past the port and runs away from it."""
    _, markers, _, _ = _run(_two_pages())
    box = _by_side(markers)[MarkerSide.OWNER].box
    length = reference_box_width(SHEET, PROFILE)
    assert box == Box(x=104 - 8 // 2, y=112 + 8, width=8, height=length)


def test_a_marker_on_a_north_port_stands_above_it_centred() -> None:
    """User: port 21 is `in`, facing N, at (704, 288). The box, turned (S20 M1), ends one stub
    short of the port and runs away from it."""
    _, markers, _, _ = _run(_two_pages())
    box = _by_side(markers)[MarkerSide.USER].box
    length = reference_box_width(SHEET, PROFILE)
    assert box == Box(x=704 - 8 // 2, y=288 - 8 - length, width=8, height=length)


def test_a_marker_on_an_east_port_grows_right_from_it() -> None:
    """Function 1's `out` faces E at (112, 96): the left edge is one stub past the port."""
    first, second = _two_pages()
    _, markers, _, _ = _run((_sideways(first), _sideways(second)))
    box = _by_side(markers)[MarkerSide.OWNER].box
    assert box == Box(x=112 + 8, y=96 - 4, width=box.width, height=8)


def test_a_marker_on_a_west_port_grows_left_from_it() -> None:
    """Function 2's `in` faces W at (696, 304): the right edge is one stub short of the port."""
    first, second = _two_pages()
    _, markers, _, _ = _run((_sideways(first), _sideways(second)))
    box = _by_side(markers)[MarkerSide.USER].box
    assert box == Box(x=696 - 8 - box.width, y=304 - 4, width=box.width, height=8)


def test_two_ports_of_one_symbol_on_opposite_sides_grow_apart() -> None:
    """The E marker's box is right of its port, the W marker's left of its own: away from both."""
    first, second = _two_pages()
    _, markers, _, _ = _run((_sideways(first), _sideways(second)))
    by = _by_side(markers)
    assert by[MarkerSide.OWNER].box.x >= by[MarkerSide.OWNER].at.x
    assert by[MarkerSide.USER].box.x + by[MarkerSide.USER].box.width <= by[MarkerSide.USER].at.x


# --- box width: fixed per sheet, never measured (LD3 (c)) ------------------------------


def test_in_one_drawing_set_a_severed_markers_box_is_the_fixed_reference_width() -> None:
    """The box carries no text: both sides share the sheet's fixed length (turned, S20 M1)."""
    _, markers, _, _ = _run(_two_pages())
    by = _by_side(markers)
    width = reference_box_width(SHEET, PROFILE)
    assert set(by) == {MarkerSide.OWNER, MarkerSide.USER}
    assert by[MarkerSide.OWNER].box.height == width
    assert by[MarkerSide.USER].box.height == width


def test_across_two_drawing_sets_a_severed_markers_box_is_still_the_fixed_width() -> None:
    """Crossing drawing sets does not change a severed marker's box: it is geometry only."""
    _, markers, _, findings = _run(_two_pages(drawing_set_of_two=2))
    by = _by_side(markers)
    width = reference_box_width(SHEET, PROFILE)
    assert set(by) == {MarkerSide.OWNER, MarkerSide.USER}
    assert by[MarkerSide.OWNER].box.height == width
    assert by[MarkerSide.USER].box.height == width
    assert findings == ()


def test_swapping_the_partners_label_swaps_the_tag_echo_prefixes() -> None:
    """A severed marker's box ignores the prefix (fixed width); `_tag_echo_text` still doesn't:
    swapping the two labels swaps the two texts (units spec U7, via a tag echo)."""
    swapped = frozendict({1: ((_C1, "C22"),), 2: ((_C2, "C1"),)})
    _, markers, requests, _ = _run(
        _two_pages(drawing_set_of_two=2),
        location_paths=swapped,
        functions=(_one_item(1), _one_item(2)),
    )
    assert markers == ()
    assert _texts(requests) == {
        hid("function", 1): "+C1p1:5C",
        hid("function", 2): "+C22p1:1A",
    }


# --- nested locations: the nearest common ancestor (units spec U7) ---------------------

_ER = hid("aspect_node", 800)
_ER_C1 = hid("aspect_node", 801)
_ER_FLD = hid("aspect_node", 802)
_AR = hid("aspect_node", 803)
_AR_C1 = hid("aspect_node", 804)


def test_a_shared_parent_prefixes_only_the_path_below_it() -> None:
    """`+ER+C1` to `+ER+FLD`: the prefix is `+FLD`, not the shared `+ER+FLD` (units spec U7).
    A severed marker's box no longer measures this at all (LD3 (c)); `_tag_echo_text` does, via
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


def test_two_same_labelled_locations_under_different_parents_are_told_apart() -> None:
    """The ambiguity U7 fixes: two nodes both labelled `C1`, one under `ER` and one under a
    different root `AR`, share no ancestor at all, so each is written by its own full path
    (`+AR+C1`, `+ER+C1`), never collapsed to the ambiguous `+C1` prefix-by-label-only would
    give (can-fail, proven live against `location_prefix`, not duplicated as a second test:
    reducing it to "the partner's leaf label alone" collides both sides on `+C1`).
    """
    paths = frozendict({1: ((_ER, "ER"), (_ER_C1, "C1")), 2: ((_AR, "AR"), (_AR_C1, "C1"))})
    _, markers, requests, _ = _run(
        _two_pages(drawing_set_of_two=2),
        location_paths=paths,
        functions=(_one_item(1), _one_item(2)),
    )
    assert markers == ()
    assert _texts(requests) == {
        hid("function", 1): "+AR+C1p1:5C",
        hid("function", 2): "+ER+C1p1:1A",
    }


def test_a_marker_carries_no_partner_drawing_set() -> None:
    """The partner is reached through the partner marker, its page and that page's drawing set."""
    names = {field.name for field in dataclasses.fields(LinkMarker)}
    assert {"drawing_set", "page", "partner_page", "box"} <= names
    assert not {"partner_drawing_set", "partner_document"} & names


# --- a partner with no location --------------------------------------------------------


def test_a_partner_in_an_unlocated_drawing_set_is_written_without_a_prefix_and_reported() -> None:
    """Set 2 has no label: the cut is still reported at set 2's port, and a severed marker's
    box is still the sheet's fixed length (C18's set-naming form is a `_tag_echo_text` concern,
    not built or measured here).
    """
    _, markers, _, findings = _run(
        _two_pages(drawing_set_of_two=2), location_paths=frozendict({1: ((_C1, "C1"),)})
    )
    by = _by_side(markers)
    width = reference_box_width(SHEET, PROFILE)
    assert set(by) == {MarkerSide.OWNER, MarkerSide.USER}
    assert by[MarkerSide.OWNER].box.height == width
    assert by[MarkerSide.USER].box.height == width
    assert [(f.code, f.severity, f.subjects) for f in findings] == [
        (LINK_PARTNER_UNLOCATED, Severity.WARNING, (hid("port", 21),))
    ]


def test_when_every_drawing_set_has_a_location_nothing_is_reported() -> None:
    """The near-identical input that passes."""
    _, _, _, findings = _run(_two_pages(drawing_set_of_two=2))
    assert findings == ()


def test_an_unlocated_set_alone_is_not_a_crossing() -> None:
    """Both ends in one drawing set that has no label: still the fixed length, and no finding."""
    _, markers, _, findings = _run(_two_pages(), location_paths=frozendict())
    assert len(markers) == 2
    assert _by_side(markers)[MarkerSide.OWNER].box.height == reference_box_width(SHEET, PROFILE)
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
    texts (LD5)."""
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
    """Set 2 has no label: C18 names the set for the coil (`p2.1:5C`), the warning at set 2's
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


def test_a_tag_echo_in_one_drawing_set_has_no_prefix_and_no_finding() -> None:
    """The near-identical input: both ends in one set, labelled or not."""
    for location_paths in (LOCATION_PATHS, frozendict()):
        decisions, markers, requests, findings = _run(
            _two_pages(), location_paths=location_paths, functions=(_one_item(1), _one_item(2))
        )
        assert [d.case for d in decisions] == [LinkCase.TAG_ECHO]
        assert markers == ()
        assert _texts(requests) == {hid("function", 1): "p2:5C", hid("function", 2): "p1:1A"}
        assert findings == ()


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
