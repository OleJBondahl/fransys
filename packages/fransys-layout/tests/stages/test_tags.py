"""The tag rules of `stages/tags.py` on hand-made values and fake `TagTexts` (D8, M4).

Every text the rules print comes from a callable of `TagTexts`; here each is a lambda returning
a fixed string, so a test names what it expects and no model is built.

Can-fail, checked by hand (each probe undone by Edit): `unit_texts` never asking `unit_tag_text`
fails the first test; `own_set_texts` without its `edges` test fails the third and fourth;
`pin_tag` leaving `text` alone fails the fifth and sixth; `pin_labels` not dropping a follower's
tag fails the sixth; `item_row_tags` not renaming the lead's slot fails the seventh;
`device_terminal_tags` labelling at `level=False` fails the eighth. `one_module_tag`'s two
probes are the `# UNDO:` lines of its two tests.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from samples import column, drawn, function_spec, hid, page_plan, placed

from fransys_layout.stages import Cell, LabelKind, LabelRequest
from fransys_layout.stages.tags import (
    TagTexts,
    _device_terminal_tags,
    _item_row_tags,
    one_module_tag,
    own_set_texts,
    pin_labels,
    pin_tag,
    unit_texts,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Id

UNIT = hid("unit", 1)


def _texts(
    is_device_terminal: Callable[[Id[Any]], bool] = lambda _function: True,
    unit_tag_text: Callable[[Id[Any], str, Id[Any]], str | None] = (
        lambda _subject, slot, _unit: f"{slot}@own"
    ),
) -> TagTexts:
    """Fake texts: each callable returns a fixed string; two can be overridden."""
    return TagTexts(
        connector_designation=lambda _function: "-X5",
        item_tag_text=lambda _item: "-F1",
        is_device_terminal=is_device_terminal,
        strip_tag_text=lambda _function: "-STRIP",
        point_text=lambda _function: "POINT",
        unit_tag_text=unit_tag_text,
    )


def _tag(number: int, *, slot: str = "tag", text: str = "old") -> LabelRequest:
    """A TAG request of function `number`."""
    return LabelRequest(kind=LabelKind.TAG, subject=hid("function", number), slot=slot, text=text)


def _marking(number: int) -> LabelRequest:
    return LabelRequest(
        kind=LabelKind.MARKING, subject=hid("function", number), slot="marking.in", text="1"
    )


def _row(*numbers: int) -> tuple:
    """One column holding functions `numbers` side by side in row 0, lane 0 first."""
    cells = tuple(
        Cell(function=hid("function", n), index=0, lane=lane) for lane, n in enumerate(numbers)
    )
    return (dataclasses.replace(column("a", ()), cells=cells),)


def _channel(number: int, module: int, *, x: int, y: int):
    """Channel `number` of PLC module `module`, drawn and placed at `(x, y)`."""
    one = dataclasses.replace(drawn(number, kind="plc_channel"), item=hid("item", module))
    return one, placed(number, x=x, y=y)


def test_one_module_tag_keeps_the_tag_of_the_leftmost_channel_of_a_row_only() -> None:
    """Channels 1 and 2 of module 9 share y: channel 2, to the right, loses its TAG only."""
    # UNDO: stages/tags.py:one_module_tag, `!= one.function` -> `== one.function` in `followers`
    #     (the leftmost channel then loses its tag and the follower keeps it)
    (d1, p1), (d2, p2) = _channel(1, 9, x=64, y=96), _channel(2, 9, x=128, y=96)
    requests = (_tag(1), _tag(2), _marking(2))
    found = one_module_tag(requests, (p2, p1), (d1, d2))  # placed order does not matter
    assert [(r.kind.value, r.subject.value[-1]) for r in found] == [
        ("tag", "1"),
        ("marking", "2"),
    ]


def test_one_module_tag_keeps_every_tag_of_other_modules_rows_and_kinds() -> None:
    """Another y, another module or a function that is no channel: each keeps its tag."""
    # UNDO: stages/tags.py:one_module_tag, `one.at.y` -> `0` in both uses of the `lead` key
    #     (channel 2, in another row of module 9, then loses its tag)
    (d1, p1), (d2, p2) = _channel(1, 9, x=64, y=96), _channel(2, 9, x=128, y=200)
    (d3, p3) = _channel(3, 8, x=192, y=96)  # module 8, at y = 96 too
    plain = placed(4, x=256, y=96, name="c")  # `drawn(4)` is a contact, no channel
    requests = tuple(_tag(n) for n in (1, 2, 3, 4))
    found = one_module_tag(requests, (p1, p2, p3, plain), (d1, d2, d3, drawn(4)))
    assert found == requests


def test_unit_texts_gives_the_units_own_functions_their_own_text() -> None:
    plan = dataclasses.replace(page_plan(("a",)), unit=UNIT)
    specs = (
        dataclasses.replace(function_spec(1), unit=UNIT),
        function_spec(2),  # no unit: keeps its text
    )
    found = unit_texts(_texts(), plan, (_tag(1), _tag(2)), specs)
    assert [(r.subject, r.text) for r in found] == [
        (hid("function", 1), "tag@own"),
        (hid("function", 2), "old"),
    ]


def test_unit_texts_texts_a_nested_units_function_for_the_set_unit() -> None:
    """A black box's function belongs to a unit below the set's: asked for the set's unit."""
    # UNDO: stages/tags.py:unit_texts, `is not None` -> `== plan.unit` (the nested function keeps
    #     its ordinary text, so its label is sized with the container's own tag in front)
    plan = dataclasses.replace(page_plan(("a",)), unit=UNIT)
    nested = (dataclasses.replace(function_spec(1), unit=hid("unit", 2)),)
    asked = _texts(unit_tag_text=lambda _subject, _slot, unit: f"for@{unit.value[-1]}")
    (found,) = unit_texts(asked, plan, (_tag(1),), nested)
    assert found.text == f"for@{UNIT.value[-1]}"


def test_unit_texts_leaves_the_top_level_and_a_declined_text_alone() -> None:
    requests = (_tag(1),)
    specs = (dataclasses.replace(function_spec(1), unit=UNIT),)
    assert unit_texts(_texts(), page_plan(("a",)), requests, specs) is requests
    plan = dataclasses.replace(page_plan(("a",)), unit=UNIT)
    declined = _texts(unit_tag_text=lambda _subject, _slot, _unit: None)
    assert unit_texts(declined, plan, requests, specs) == requests


def test_own_set_texts_skips_the_boundary_functions() -> None:
    inside = dataclasses.replace(function_spec(1), unit=UNIT)
    boundary = dataclasses.replace(function_spec(2), unit=UNIT)
    pin = dataclasses.replace(function_spec(3), unit=UNIT, pin_function=hid("function", 4))
    bare = function_spec(5)  # no unit
    specs = (inside, boundary, pin, bare)
    requests = tuple(_tag(n) for n in (1, 2, 3, 5))
    edges = frozenset({hid("function", 2), hid("function", 4)})  # a pin view: its connector
    found = own_set_texts(_texts(), edges, requests, specs)
    assert [r.text for r in found] == ["tag@own", "old", "old", "old"]


def test_own_set_texts_needs_the_edge_test_for_a_unit_function() -> None:
    """The one function of the unit is in no edge set: it takes the text; in the set, it keeps."""
    specs = (dataclasses.replace(function_spec(1), unit=UNIT),)
    assert own_set_texts(_texts(), frozenset(), (_tag(1),), specs)[0].text == "tag@own"
    assert (
        own_set_texts(_texts(), frozenset({hid("function", 1)}), (_tag(1),), specs)[0].text == "old"
    )


def test_pin_tag_takes_the_connector_text_on_a_lead_and_the_pin_slot_off_it() -> None:
    connector = hid("function", 10)
    request = _tag(1, slot="tag", text="-X5:1")
    lead = pin_tag(_texts(), request, connector, frozenset({request.subject}))
    assert (lead.slot, lead.text) == ("tag.conn", "-X5")
    other = pin_tag(_texts(), request, connector, frozenset())
    assert (other.slot, other.text) == ("tag.pin", "-X5:1")


def test_pin_labels_shows_the_connector_once_and_a_lone_pin_its_full_tag() -> None:
    connector = hid("function", 10)
    pins = tuple(dataclasses.replace(function_spec(n), pin_function=connector) for n in (1, 2, 3))
    lone = dataclasses.replace(column("b", ()), cells=(Cell(function=hid("function", 3), index=0),))
    columns = (*_row(1, 2), lone)
    requests = (_tag(1, text="-X5:1"), _tag(2, text="-X5:2"), _tag(3, text="-X5:3"))
    requests = (*requests, _marking(1), _marking(2), _marking(3))
    found = pin_labels(_texts(), requests, columns, pins)
    assert [(r.kind.value, r.subject.value[-1], r.slot, r.text) for r in found] == [
        ("tag", "1", "tag.conn", "-X5"),  # the row's lead, in the connector's text
        ("tag", "3", "tag.pin", "-X5:3"),  # a pin alone in its row: its full pin tag
        ("marking", "1", "marking.in", "1"),
        ("marking", "2", "marking.in", "1"),  # a row of pins: every pin its marking
    ]


def test_item_row_tags_puts_the_item_tag_on_lane_0_only() -> None:
    same_item = hid("item", 7)
    contact = dataclasses.replace(function_spec(1, kind="contact_no"), item=same_item)
    passthrough = dataclasses.replace(
        function_spec(2, kind="terminal"), item=same_item, point_text="N"
    )
    requests = (_tag(1, text="old1"), _tag(2, text="old2"))
    found = _item_row_tags(_texts(), _row(1, 2), (contact, passthrough), requests)
    assert [(r.subject, r.slot, r.text, r.level) for r in found] == [
        (hid("function", 1), "tag.item", "-F1", False),  # the lead: the item's tag
        (hid("function", 2), "tag.point", "N", True),  # a follower: no tag, its point text
    ]


def test_device_terminal_tags_labels_the_terminal_strip_and_point() -> None:
    terminal = function_spec(1, kind="terminal")
    other = _tag(9, text="kept")
    found = _device_terminal_tags(_texts(), (terminal,), (_tag(1), other))
    assert [(r.subject, r.slot, r.text, r.level) for r in found] == [
        (hid("function", 9), "tag", "kept", False),
        (hid("function", 1), "tag.strip", "-STRIP", True),
        (hid("function", 1), "tag.point", "POINT", True),
    ]
    not_device = _texts(is_device_terminal=lambda _function: False)
    assert _device_terminal_tags(not_device, (terminal,), (_tag(1), other)) == (_tag(1), other)
    contact = function_spec(1)  # not a terminal kind
    assert _device_terminal_tags(_texts(), (contact,), (_tag(1), other)) == (_tag(1), other)
