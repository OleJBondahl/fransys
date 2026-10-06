"""CONTACT-STATES CS5 tests: a coil's contact image reads a changeover's throws by role.

`contact_image` (through `label_text`, slot "contacts") lists each make throw under NO and each
break throw under NC, the port names as the part prints them; no test here depends on a digit.
"""

from decimal import Decimal
from typing import Any

import pytest
from contact_builders import _ITEM_KEY, _NUMBERED, _bundle, _function, _port
from derive_helpers import add_all
from examples import bundle_records

from fransys_model.derive.drawing_text import frame_column, frame_row, label_text, position_text
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    CrossReferencePartner,
    DrawingSet,
    Label,
    LabelKind,
    Orientation,
    Page,
    PageRole,
    SheetFormat,
    SymbolPlacement,
)
from fransys_model.vocab.enums import FunctionKind, PortRole
from fransys_model.vocab.instantiate import instantiate

_PRODUCED_BY = "test-engine 0.0.0"
_COLUMNS = 8
_ROWS = 6
_X = 100  # every contact's partner x: one column on page 2
_Y = 50  # every contact's partner y: one row on page 2 (`_partner_row` reads a placement's y)
_WHERE = position_text(
    2, frame_column(1280, _COLUMNS, _X), frame_row(822, _ROWS, _Y), ()
)  # 1280/822: this file's sheet content width/height in grid units (400/257 mm at 2.5 mm/module)

type _Poles = tuple[tuple[str, str, str], ...]


def _image(  # noqa: PLR0913 -- a test builder; every option is a keyword with a default
    origin: Origin,
    poles: _Poles,
    *,
    generic: bool = False,
    kind: FunctionKind = FunctionKind.CONTACT_CO,
    extra: tuple[Any, ...] = (),
    listed: int | None = None,
) -> list[str]:
    """The lines of the contact image of a coil whose relay has one changeover per pole.

    Each pole is (common, break, make) port names; the image's partners are the poles' commons on
    page 2, the label is on page 1 of the same set. `generic` gives every port the role GENERIC;
    `kind` is every function's kind. `listed` keeps the first that many poles as partners; `extra`
    are more records of the model.
    """
    bundle = (
        _bundle(poles, roles=(PortRole.GENERIC, PortRole.GENERIC, PortRole.GENERIC))
        if generic
        else _bundle(poles, kind=kind)
    )
    draft = Draft()
    add_all(draft, *bundle_records(bundle), *instantiate(bundle, _ITEM_KEY), origin=origin)
    sheet = SheetFormat(
        id=make_id(SheetFormat, ("sheet",)),
        key=("sheet",),
        name="test sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=_COLUMNS,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, ("set",)),
        key=("set",),
        location=None,
        number=1,
        produced_by=_PRODUCED_BY,
    )
    pages = [
        Page(
            id=make_id(Page, ("page", str(number))),
            key=("page", str(number)),
            drawing_set=drawing_set.id,
            number=number,
            role=PageRole.CONTROL,
            sheet_format=sheet.id,
            groups=(),
            produced_by=_PRODUCED_BY,
        )
        for number in (1, 2)
    ]
    add_all(draft, sheet, drawing_set, *pages, *extra, origin=origin)
    label = Label(
        id=make_id(Label, ("image",)),
        key=("image",),
        page=pages[0].id,
        function=_function(1),
        port=None,
        conductor=None,
        kind=LabelKind.CROSS_REFERENCE,
        slot="contacts",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by=_PRODUCED_BY,
        partners=tuple(
            CrossReferencePartner(port=_port(number, names[0]), page=pages[1].id, x=_X)
            for number, names in enumerate(poles[:listed], start=1)
        ),
    )
    placements = [
        SymbolPlacement(
            id=make_id(SymbolPlacement, ("placement", str(number))),
            key=("placement", str(number)),
            function=_function(number),
            page=pages[1].id,
            x=_X,
            y=_Y,
            orientation=Orientation.R0,
            poles=1,
            symbol="generic",
            library_version="0.0.0",
            produced_by=_PRODUCED_BY,
        )
        for number in range(1, len(poles) + 1)
    ]
    add_all(draft, *placements, origin=origin)
    return label_text(freeze(draft), label).split("\n")


@pytest.mark.parametrize(
    ("names", "make", "brk"),
    [
        (_NUMBERED, "11-14", "11-12"),
        (("COM", "NC", "NO"), "COM-NO", "COM-NC"),
        (("I", "II", "III"), "I-III", "I-II"),
    ],
)
def test_a_changeover_lists_its_make_under_no_and_its_break_under_nc(
    origin: Origin, names: tuple[str, str, str], make: str, brk: str
) -> None:
    """The printed names are substituted; roles decide the column, never a digit."""
    assert _image(origin, (names,)) == ["NO | NC", f"{make} {_WHERE} | {brk} {_WHERE}"]


def test_a_changeover_of_generic_ports_gives_no_entry(origin: Origin) -> None:
    """A part with no throw roles has no known throws: an empty image, no raise."""
    assert _image(origin, (_NUMBERED,), generic=True) == ["NO | NC"]


def test_a_two_pole_changeover_lists_both_poles_in_number_order(origin: Origin) -> None:
    """Each pole gives its own entry, ordered by the common's number as before."""
    assert _image(origin, (("21", "22", "24"), _NUMBERED)) == [
        "NO | NC",
        f"11-14 {_WHERE} | 11-12 {_WHERE}",
        f"21-24 {_WHERE} | 21-22 {_WHERE}",
    ]


def test_a_named_common_sorts_after_every_numbered_one(origin: Origin) -> None:
    """The order is numbered commons by number, then named commons by name."""
    poles: _Poles = (("COM", "NC", "NO"), ("21", "22", "24"), _NUMBERED, ("A", "B", "C"))
    assert _image(origin, poles) == [
        "NO | NC",
        f"11-14 {_WHERE} | 11-12 {_WHERE}",
        f"21-24 {_WHERE} | 21-22 {_WHERE}",
        f"A-C {_WHERE} | A-B {_WHERE}",
        f"COM-NO {_WHERE} | COM-NC {_WHERE}",
    ]
