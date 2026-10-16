"""A reference layout measures names the drawing set by its rank in its unit (render-0018).

The invented shape: two units, set 1 (unit A) and set 2 (unit B). B's first set is numbered 2,
so it is set 1 of B's own PDF and a reference to it prints `p1.<page>` like derive's
`page_reference_text`, `page_destination` and render's check text (R21, designer 2026-10-16).
Each of the three layout sites that build a reference text is tested on its own.
"""

import dataclasses

import pytest
from samples import PROFILE, SHEET, built_links, connection, drawn, hid, page_plan, placed
from test_images import MARKS, _relay_function

from fransys_layout.stages._image_widest import cross_form, widest_where
from fransys_layout.stages.images import ImageInputs, contact_images
from fransys_model.derive.drawing_text import position_text

_NO_PATHS = frozendict()  # no location, so a place in another set names its set: `p<k>.<page>`


def _plan(drawing_set: int, unit: int, number: int = 1):
    return dataclasses.replace(
        page_plan(("a",), number=number), drawing_set=drawing_set, unit=hid("unit", unit)
    )


def _in_set(function, drawing_set: int):
    return dataclasses.replace(function, drawing_set=drawing_set)


def test_a_contact_image_names_a_coil_in_a_units_first_set_by_its_rank() -> None:
    coil = _relay_function(1, "coil", "A1", "A2")
    make = _relay_function(2, "contact_no", "13", "14")
    inputs = ImageInputs((make, coil), SHEET, PROFILE, MARKS, no_place="N/A")
    plans = (_plan(1, unit=1), _plan(2, unit=2))
    coil_page = (_in_set(placed(1, x=0, y=0), 2),)
    make_page = (_in_set(placed(2, x=200, y=0), 1),)
    _, requests = contact_images(plans, [(make_page, ()), (coil_page, ())], inputs)
    (request,) = requests
    # UNDO: stages/images.py `_seat`: `ranks.get(...)` -> `one.drawing_set`
    assert request.text == position_text(1, 1, "A", (), set_number=1)


def test_a_tag_echo_names_the_partner_in_a_units_first_set_by_its_rank() -> None:
    _, _, requests, _ = built_links(
        (connection(1, 1, 2),),
        (),
        (_in_set(placed(1, x=104, y=96), 1), _in_set(placed(2, x=704, y=96), 2)),
        (drawn(1), dataclasses.replace(drawn(2, kind="contact_no"), item=hid("item", 1))),
        sheet=SHEET,
        profile=PROFILE,
        location_paths=_NO_PATHS,
        units=frozendict(),
        function_units=frozendict(),
        ranks=frozendict({1: 1, 2: 1}),
    )
    # UNDO: stages/texts/echoes.py `_tag_echo_text`: `ranks.get(...)` -> `end.page[0]`
    assert [r.text for r in requests] == ["p1.1:5A", "p1.1:1A"]


def test_the_widest_cross_set_text_is_measured_with_ranks() -> None:
    plans = (_plan(1, unit=1), _plan(2, unit=2))
    cross = cross_form(plans, {})
    # UNDO: stages/_image_widest.py `cross_form`: `set_ranks(...)` -> the plans' set numbers
    assert cross == (1, ())
    assert widest_where(1, SHEET, PROFILE, cross).startswith("p1.1:")


def test_a_missing_rank_is_an_error_naming_the_set() -> None:
    # UNDO: stages/lookups.py `set_rank`: raise -> `return ranks.get(drawing_set, drawing_set)`
    with pytest.raises(ValueError, match="drawing set 1 has no rank"):
        built_links(
            (connection(1, 1, 2),),
            (),
            (_in_set(placed(1, x=104, y=96), 1), _in_set(placed(2, x=704, y=96), 2)),
            (drawn(1), dataclasses.replace(drawn(2, kind="contact_no"), item=hid("item", 1))),
            sheet=SHEET,
            profile=PROFILE,
            location_paths=_NO_PATHS,
            units=frozendict(),
            function_units=frozendict(),
            ranks=frozendict(),
        )


def test_a_contact_image_without_a_rank_is_an_error_naming_the_set() -> None:
    coil = _relay_function(1, "coil", "A1", "A2")
    make = _relay_function(2, "contact_no", "13", "14")
    inputs = ImageInputs((make, coil), SHEET, PROFILE, MARKS, no_place="N/A")
    plans = (_plan(1, unit=1),)  # no plan for set 2, so set 2 has no rank
    pages = [((_in_set(placed(2, x=200, y=0), 1),), ()), ((_in_set(placed(1, x=0, y=0), 2),), ())]
    with pytest.raises(ValueError, match="drawing set 2 has no rank"):
        contact_images(plans, pages, inputs)
