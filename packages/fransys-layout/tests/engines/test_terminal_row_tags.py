"""D12 (item-only strip text): a run of terminals is the terminals of one strip, not of one text.

At top level a strip's text is its item designation only ("-X2"), so two different strips of
one designation (`+ER+C1-X2`, `+ER+C2-X2`) print the same text: the run groups by the strip
item, which `FunctionSpec.item_parent` names.

Can-fail, checked by hand: with `terminal_row_tags` grouping by `strip_text` alone the second
test fails.
"""

import dataclasses

from samples import function_spec, hid

from fransys_layout.stages import Cell, Column, LabelKind, LabelRequest, Role
from fransys_layout.stages.tags import _terminal_row_tags


def _terminal(number: int, *, strip: int):
    """Terminal `number` of the strip item `strip`, printing the strip text "-X2"."""
    return dataclasses.replace(
        function_spec(number, kind="terminal"),
        strip_text="-X2",
        point_text=f"1:{number}",
        item_parent=hid("item", strip),
    )


def _row_tags(*strips: int) -> tuple[LabelRequest, ...]:
    """The tag requests of one column row holding one terminal of each of `strips`."""
    specs = tuple(_terminal(number, strip=strip) for number, strip in enumerate(strips, start=1))
    column = Column(
        key=("invented", "row"),
        cells=tuple(
            Cell(function=spec.function, index=0, lane=lane) for lane, spec in enumerate(specs)
        ),
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    requests = tuple(
        LabelRequest(kind=LabelKind.TAG, subject=spec.function, slot="tag", text="-X2:1")
        for spec in specs
    )
    return _terminal_row_tags((column,), specs, requests)


def test_two_terminals_of_one_strip_in_a_row_are_a_run() -> None:
    slots = sorted(request.slot for request in _row_tags(7, 7))
    assert slots == ["tag.point", "tag.point", "tag.strip"]


def test_two_strips_of_one_designation_in_a_row_are_no_run() -> None:
    tags = _row_tags(7, 8)  # two strips both printing "-X2"
    assert [request.slot for request in tags] == ["tag", "tag"]
