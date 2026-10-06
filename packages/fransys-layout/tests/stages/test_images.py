"""The contact-image rules: hand-made values, no model and no engine."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from samples import PROFILE, SHEET, column, function_spec, hid, page_plan, placed

from fransys_layout.geometry import WIRING_GRID, Box
from fransys_layout.stages import FunctionSpec, LabelKind, PortSpec, RequestPartner, Role
from fransys_layout.stages.images import (
    ImageInputs,
    _image_marks,
    _image_width,
    _page_marker_boxes,
    contact_images,
    image_reserves,
)
from fransys_layout.stages.types import Cell


def _relay_function(number: int, kind: str, *names: str, item: int = 1) -> FunctionSpec:
    """Function `number` of relay item `item`, of `kind`, with one model port per name."""
    ports = tuple(
        PortSpec(
            port=hid("port", number * 10 + i),
            name=name,
            physical_net=hid("net", number * 10 + i),
            role=Role.CONTROL,
        )
        for i, name in enumerate(names)
    )
    return replace(function_spec(number, kind=kind), item=hid("item", item), ports=ports)


# The marks each contact function lists, as the engine reads them of the model
# (`derive.drawing_text.contact_marks`): hand-made here, the layout has no model in these tests.
MARKS = {
    hid("function", 2): (["13-14"], []),
    hid("function", 3): ([], ["21-22"]),
}

# --- image_marks ---------------------------------------------------------------------


def test_image_marks_collect_each_contacts_no_and_nc_marks_in_order() -> None:
    """A changeover's marks stand in both columns, a plain contact's in one."""
    # UNDO: stages/images.py:image_marks, swap `marks[s.function][0]` and `marks[s.function][1]`
    change = _relay_function(1, "contact_co", "11", "12", "14")
    make = _relay_function(2, "contact_no", "13", "14")
    marks = {change.function: (["11-14"], ["11-12"]), make.function: (["13-14"], [])}
    assert _image_marks([change, make], marks) == (["11-14", "13-14"], ["11-12"])


# --- image_reserves ------------------------------------------------------------------


def _relay() -> tuple[FunctionSpec, ...]:
    """A coil (function 1) and its NO contact (function 2), one item; function 3 is another item."""
    return (
        _relay_function(1, "coil", "A1", "A2"),
        _relay_function(2, "contact_no", "13", "14"),
        function_spec(3),
    )


def test_a_coil_with_contacts_reserves_room_below_its_last_cell_and_width_on_its_lane() -> None:
    """The room (2 text rows + 1 text row, 0 padding) is kept below the last cell under the coil.

    Both cells of the lane keep the image's width free; the coil's entry marks are "13-14".
    """
    # UNDO: stages/images.py:image_reserves, `if spec.roles.contact:` -> `if False:`
    #     (no contact is grouped under its coil, so no coil reserves anything)
    cells = column("a", (1, 3))
    reserves = image_reserves((cells,), _relay(), PROFILE, MARKS)
    coil, under = (hid("function", n) for n in (1, 3))
    down = (1 + 1) * PROFILE.text_height + PROFILE.text_height
    assert set(reserves) == {(cells.key, coil), (cells.key, under)}
    assert (reserves[cells.key, coil].down, reserves[cells.key, under].down) == (0, down)
    image = (coil, ("13-14",), False)
    assert reserves[cells.key, coil].images == reserves[cells.key, under].images == (image,)


@pytest.mark.parametrize("own", [{"replica": True}, {"host": hid("function", 9)}])
def test_a_replica_or_a_hosted_coil_reserves_nothing(own: dict) -> None:
    """A replica cell and an attachment (a cell with a host) hold no contact image."""
    # UNDO: stages/images.py:image_reserves, drop `cell.replica or cell.host is not None or`
    cells = replace(column("a", (1,)), cells=(Cell(function=hid("function", 1), index=0, **own),))
    assert image_reserves((cells,), _relay(), PROFILE, MARKS) == {}


def test_a_contact_alone_or_a_coil_without_contacts_reserves_nothing() -> None:
    """Only a coil (roles.coil) with at least one contact reserves room."""
    # UNDO: stages/images.py:image_reserves, `not spec.roles.coil` -> `False`
    #     (the contact's own cell then reserves too)
    relay = _relay()
    assert image_reserves((column("a", (2,)),), relay, PROFILE, MARKS) == {}
    assert image_reserves((column("a", (1,)),), relay[:1], PROFILE, MARKS) == {}


# --- contact_images ------------------------------------------------------------------


def test_one_coil_with_two_contacts_gives_one_contacts_label_and_a_reference_per_contact() -> None:
    """The coil at x = 0 on column "a", its NO at x = 200 and NC at x = 800 on column "b".

    The label sits under the coil's keep-out from G / 2 right of its first port, as wide as the
    image measures its two entries (which end in each contact's place: "2A" and "6A");
    each contact gets a reference to "1A", the coil's place, under its tag.
    """
    # UNDO: stages/images.py:contact_images, `s.roles.contact` -> `s.roles.contact_closed`
    #     (the NO contact is no contact: only the NC one is listed)
    coil = _relay_function(1, "coil", "A1", "A2")
    make = _relay_function(2, "contact_no", "13", "14")
    brake = _relay_function(3, "contact_nc", "21", "22")
    page = (
        placed(1, x=0, y=0, name="a"),
        placed(2, x=200, y=0, name="b"),
        placed(3, x=800, y=0, name="b"),
    )
    inputs = ImageInputs((brake, make, coil), SHEET, PROFILE, MARKS, no_place="N/A")
    (found,), requests = contact_images((page_plan(("a", "b")),), [(page, ())], inputs)
    assert found[0] == page
    (label,) = found[1]
    width = _image_width(["13-14 2A", "21-22 6A"], PROFILE)
    keepout = page[0].geometry.keepout
    expected = Box(
        x=WIRING_GRID // 2,
        y=keepout.y + keepout.height + PROFILE.marker_padding,
        width=width,
        height=(1 + 1) * PROFILE.text_height + 3 * PROFILE.marker_padding,
    )
    assert (label.kind, label.subject, label.slot, label.box) == (
        LabelKind.CROSS_REFERENCE,
        coil.function,
        "contacts",
        expected,
    )
    assert label.partners == (
        RequestPartner(port=make.ports[0].port, drawing_set=1, page=1, x=200),
        RequestPartner(port=brake.ports[0].port, drawing_set=1, page=1, x=800),
    )
    assert [(r.subject, r.slot, r.text) for r in requests] == [
        (make.function, "tag", "1A"),
        (brake.function, "tag", "1A"),
    ]
    assert all(
        r.partners == (RequestPartner(port=coil.ports[0].port, drawing_set=1, page=1, x=0),)
        for r in requests
    )


def test_a_coil_held_by_two_pages_hangs_its_image_by_the_first_page() -> None:
    """The coil stands on both page tuples; only the second has a cell under it (column "a").

    The image is placed by the first page holding the coil (D10: the mapping is built once, first
    page wins, as the scan it replaced): the coil's row rule, not the second page's column foot.
    """
    # UNDO: stages/images.py:_page_holding, `found.setdefault(key, placed)` ->
    #     `found[key] = placed` (the last page wins: the foot rule below the second page's cell)
    coil = _relay_function(1, "coil", "A1", "A2")
    make = _relay_function(2, "contact_no", "13", "14")
    coil_at = placed(1, x=0, y=0, name="a")
    first = (coil_at, placed(2, x=200, y=0, name="b"))
    second = (coil_at, placed(4, x=0, y=104, name="a"))
    inputs = ImageInputs((make, coil), SHEET, PROFILE, MARKS, no_place="N/A")
    plans = (page_plan(("a", "b")), page_plan(("a",), number=2))
    (found, _), _ = contact_images(plans, [(first, ()), (second, ())], inputs)
    (label,) = found[1]
    keepout = coil_at.geometry.keepout
    assert label.box.y == keepout.y + keepout.height + PROFILE.marker_padding


def test_the_markers_of_a_page_are_grouped_once_in_their_order() -> None:
    """Each `(drawing_set, page)` maps to its markers' boxes in `markers` order."""
    # UNDO: stages/slices.py:page_of, `item.drawing_set, item.page` -> `item.drawing_set, 1`
    marks = [
        SimpleNamespace(drawing_set=1, page=page, box=box)
        for page, box in ((1, "a"), (2, "b"), (1, "c"))
    ]
    assert _page_marker_boxes(tuple(marks)) == {(1, 1): ["a", "c"], (1, 2): ["b"]}


def test_a_spare_contact_counts_in_the_room_the_coil_reserves() -> None:
    """V1: the engine hands the spares in with the drawn functions; a second NO mark adds a row."""
    # UNDO: engine.py `every` -> `inputs.functions` in the `image_reserves` call
    spare = _relay_function(4, "contact_no", "15", "16")
    marks = {**MARKS, spare.function: (["15-16"], [])}
    cells = column("a", (1, 3))
    coil = hid("function", 1)
    one = image_reserves((cells,), _relay(), PROFILE, marks)
    two = image_reserves((cells,), (*_relay(), spare), PROFILE, marks)
    assert two[cells.key, coil].images == ((coil, ("13-14", "15-16"), False),)
    last = hid("function", 3)
    assert two[cells.key, last].down - one[cells.key, last].down == PROFILE.text_height


def test_a_spare_contact_is_listed_n_a_with_no_partner_and_no_reference() -> None:
    """V1: the table gains a "15-16 N/A" row; only the drawn contact has a partner."""
    # UNDO: stages/images.py:contact_images, the `_entry_text(mark, inputs.no_place)` rows removed
    coil = _relay_function(1, "coil", "A1", "A2")
    make = _relay_function(2, "contact_no", "13", "14")
    spare = _relay_function(4, "contact_no", "15", "16")
    marks = {**MARKS, spare.function: (["15-16"], [])}
    page = (placed(1, x=0, y=0, name="a"), placed(2, x=200, y=0, name="b"))
    inputs = ImageInputs((make, coil), SHEET, PROFILE, marks, None, (spare,), no_place="N/A")
    (found,), requests = contact_images((page_plan(("a", "b")),), [(page, ())], inputs)
    (label,) = found[1]
    assert label.box.height == (1 + 2) * PROFILE.text_height + 3 * PROFILE.marker_padding
    assert label.box.width == _image_width(["13-14 2A", "15-16 N/A"], PROFILE)
    assert label.partners == (
        RequestPartner(port=make.ports[0].port, drawing_set=1, page=1, x=200),
    )
    assert [(r.subject, r.slot) for r in requests] == [(make.function, "tag")]


# --- V10: a block's contacts belong to the device that owns it ----------------------------


def _block(owner_kind: str) -> tuple[tuple[FunctionSpec, ...], dict, tuple, ImageInputs]:
    """Owner item 1 (function 1 of `owner_kind`), a block item 2 with an NO contact (function 2).

    The owner stands at x = 0 and the block's contact at x = 200 on the one page.
    """
    main = _relay_function(1, owner_kind, "A1", "A2")
    contact = _relay_function(2, "contact_no", "53", "54", item=2)
    owners = {contact.function: main.item}
    page = (placed(1, x=0, y=0, name="a"), placed(2, x=200, y=0, name="b"))
    return (
        (main, contact),
        owners,
        page,
        ImageInputs((contact, main), SHEET, PROFILE, MARKS, owners, no_place="N/A"),
    )


def test_a_blocks_contacts_are_listed_in_the_owners_coil_image() -> None:
    """The owner's coil lists the block's contact and the contact refers back to the coil."""
    # UNDO: stages/images.py:contact_images, `inputs.owners` -> `None` (each item its own group:
    #     the block's contact has no coil, so no image and no reference)
    (coil, contact), _, page, inputs = _block("coil")
    (found,), requests = contact_images((page_plan(("a", "b")),), [(page, ())], inputs)
    (label,) = found[1]
    assert label.partners == (
        RequestPartner(port=contact.ports[0].port, drawing_set=1, page=1, x=200),
    )
    assert [(r.subject, r.text) for r in requests] == [(contact.function, "1A")]
    assert requests[0].partners[0].port == coil.ports[0].port


def test_a_block_on_a_device_without_a_coil_refers_to_its_main_symbol_and_has_no_image() -> None:
    """A breaker (a protection function) with a block: one reference to the breaker, no table."""
    # UNDO: stages/images.py:contact_images, `main = coil or next(...)` -> `main = coil`
    #     (no coil, no reference)
    (breaker, contact), _, page, inputs = _block("protection")
    (found,), requests = contact_images((page_plan(("a", "b")),), [(page, ())], inputs)
    assert found[1] == ()
    assert [(r.subject, r.slot, r.text) for r in requests] == [(contact.function, "tag", "1A")]
    assert requests[0].partners[0].port == breaker.ports[0].port


def _own_and_block_refs(owner_kind: str, *, owner_placed: bool = True) -> dict[int, tuple]:
    """Owner item 1 (function 1 of `owner_kind`, another main symbol function 4), its own NO
    contact (function 2) and a block's (item 2, function 3): the references each contact gets."""
    main = _relay_function(1, owner_kind, "A1", "A2")
    own = _relay_function(2, "contact_no", "13", "14")
    block = _relay_function(3, "contact_no", "53", "54", item=2)
    other = _relay_function(4, "protection", "1", "2")
    owners = {block.function: main.item, own.function: main.item}
    shown = [placed(2, x=104, y=0, name="b"), placed(3, x=200, y=0, name="c")]
    shown += [placed(4, x=304, y=0, name="d")] + ([placed(1, x=0, y=0)] if owner_placed else [])
    inputs = ImageInputs((main, own, block, other), SHEET, PROFILE, MARKS, owners, no_place="N/A")
    _, requests = contact_images((page_plan(("a", "b", "c", "d")),), [(tuple(shown), ())], inputs)
    return {
        n: tuple((r.text, r.partners[0].port) for r in requests if r.subject == hid("function", n))
        for n in (2, 3)
    }


def test_a_blocks_contact_gets_the_reference_the_devices_own_contact_gets() -> None:
    """One path: placed coil, no coil, or an unplaced coil, the block's contact is like the own."""
    # UNDO: stages/images.py:contact_images, `home_references(contacts, main, ...)` in the no-coil
    #     branch -> only the contacts with `s.item != main.item` (a separate block path)
    for kind, placed_ in (("coil", True), ("protection", True), ("coil", False)):
        refs = _own_and_block_refs(kind, owner_placed=placed_)
        assert refs[2] == refs[3], (kind, placed_)
    placed_coil = _own_and_block_refs("coil")
    assert placed_coil[2][0][1] == hid("port", 10 + 0)
    assert _own_and_block_refs("coil", owner_placed=False) == {2: (), 3: ()}


def test_a_blocks_contact_marks_count_in_the_owners_reserve() -> None:
    """The coil's reserved room is sized for the block's contact too: its mark is in `images`."""
    # UNDO: stages/images.py:image_reserves, `by_owner(..., owners)` -> `by_owner(..., None)`
    (coil, contact), owners, _, _ = _block("coil")
    cells = column("a", (1,))
    reserves = image_reserves((cells,), (coil, contact), PROFILE, MARKS, owners)
    assert reserves[cells.key, coil.function].images == ((coil.function, ("13-14",), False),)


def test_a_contact_in_another_drawing_set_marks_the_image_cross_set() -> None:
    """RW9: the image is flagged when a contact of the coil's item is in another set."""
    # UNDO: stages/images.py:image_reserves, `cross = any(...)` -> `cross = False`
    coil, make, other = _relay()
    far = replace(make, location_path=(hid("aspect_node", 7),))
    cells = column("a", (1, 3))
    near = image_reserves((cells,), (coil, make, other), PROFILE, MARKS)
    apart = image_reserves((cells,), (coil, far, other), PROFILE, MARKS)
    key = cells.key, coil.function
    assert [cross for *_, cross in near[key].images] == [False]
    assert [cross for *_, cross in apart[key].images] == [True]
