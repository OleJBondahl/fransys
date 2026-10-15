"""`reference_slot` (decision model-0255): a net reference's colour slot is `(#n - 1) % 8`.

Hand-built records, as `test_drawing_text.py`: each net is one `REF` marker and one `BRANCH`
marker on a last page; an unnumbered off stub stands beside them.
"""

import itertools
from dataclasses import replace
from decimal import Decimal
from typing import Any
lazy from collections.abc import Sequence

import pytest
from derive_helpers import add_all

from fransys_model.derive.marker_text import REF_SLOTS, reference_number, reference_slot
from fransys_model.kernel import Draft, Id, Model, Origin, freeze
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    PageRole,
    SheetFormat,
    Side,
    StarKind,
    layout_of,
)
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortRole

LAST_PAGE = 99
PRODUCED_BY = "test-engine 0.0.0"


def _key(id_: Id[Any]) -> tuple[str, ...]:
    return (str(id_.value)[:8],)


def _marker(id_: Id[Any], page: Page, port: Port, star: StarKind, partner: Id[Any]) -> LinkMarker:
    return LinkMarker(
        id=id_,
        key=_key(id_),
        page=page.id,
        port=port.id,
        side=MarkerSide.USER if star is StarKind.BRANCH else MarkerSide.OWNER,
        partner=partner,
        star=star,
        x=0,
        y=0,
        width=13,
        height=8,
        produced_by=PRODUCED_BY,
        facing=Side.E,
        far=port.id if star is StarKind.OFF else None,
    )


def _build(
    origin: Origin, ref_places: Sequence[tuple[int, int]]
) -> tuple[Model, list[LinkMarker], LinkMarker]:
    """A model with one net per `(page number, x)`; returns it, the REFs in order, the off stub."""
    counter = itertools.count(1)

    def new_id(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    sheet_id = new_id("layout.sheet_format")
    sheet = SheetFormat(
        id=sheet_id,
        key=_key(sheet_id),
        name="s",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    ds_id = new_id("layout.drawing_set")
    ds = DrawingSet(id=ds_id, key=_key(ds_id), location=None, number=1, produced_by=PRODUCED_BY)
    pages: dict[int, Page] = {}
    for n in sorted({n for n, _ in ref_places} | {LAST_PAGE}):
        page_id = new_id("layout.page")
        pages[n] = Page(
            id=page_id,
            key=_key(page_id),
            drawing_set=ds.id,
            number=n,
            role=PageRole.CONTROL,
            sheet_format=sheet.id,
            groups=(),
            produced_by=PRODUCED_BY,
        )
    item_id, fn_id = new_id("item"), new_id("function")
    item = Item(
        id=item_id,
        key=_key(item_id),
        part=None,
        parent=None,
        position=None,
        tag="K1",
        description="invented",
    )
    fn = Function(
        id=fn_id,
        key=_key(fn_id),
        item=item.id,
        template=None,
        name="fn",
        kind=FunctionKind.COIL,
    )
    ports = [
        Port(
            id=(port_id := new_id("port")),
            key=_key(port_id),
            function=fn.id,
            template=None,
            name=str(k),
            role=PortRole.GENERIC,
        )
        for k in range(2 * len(ref_places) + 1)
    ]
    refs: list[LinkMarker] = []
    branches: list[LinkMarker] = []
    for k, (n, x) in enumerate(ref_places):
        ref_id = new_id("layout.link_marker")
        refs.append(replace(_marker(ref_id, pages[n], ports[2 * k], StarKind.REF, ref_id), x=x))
        branch_id = new_id("layout.link_marker")
        branches.append(
            _marker(
                branch_id,
                pages[LAST_PAGE],
                ports[2 * k + 1],
                StarKind.BRANCH,
                ref_id,
            )
        )
    stub_id = new_id("layout.link_marker")
    stub = _marker(stub_id, pages[LAST_PAGE], ports[-1], StarKind.OFF, stub_id)
    draft = Draft()
    add_all(
        draft, sheet, ds, *pages.values(), item, fn, *ports, *refs, *branches, stub, origin=origin
    )
    return freeze(draft), refs, stub


def test_the_slot_is_the_number_less_one_modulo_eight(origin: Origin) -> None:
    model, refs, _ = _build(origin, [(n, 0) for n in range(1, 4)])
    assert [reference_number(model, r) for r in refs] == [1, 2, 3]
    assert [reference_slot(model, r) for r in refs] == [0, 1, 2]


def test_both_ends_of_a_net_on_different_pages_share_a_slot(origin: Origin) -> None:
    model, refs, _ = _build(origin, [(1, 0), (2, 0)])
    markers = layout_of(model, LinkMarker)
    for ref in refs:
        branch = next(m for m in markers.values() if m.partner == ref.id and m.id != ref.id)
        assert branch.page != ref.page
        assert reference_slot(model, branch) == reference_slot(model, ref) is not None
    assert reference_slot(model, refs[0]) != reference_slot(model, refs[1])


def test_two_nets_on_one_page_take_different_slots(origin: Origin) -> None:
    model, refs, _ = _build(origin, [(1, 0), (1, 400)])
    assert refs[0].page == refs[1].page
    assert [reference_slot(model, r) for r in refs] == [0, 1]


def test_an_unnumbered_off_stub_has_no_slot(origin: Origin) -> None:
    model, _, stub = _build(origin, [(1, 0)])
    with pytest.raises(KeyError):
        reference_number(model, stub)
    assert reference_slot(model, stub) is None


def test_the_ninth_net_wraps_to_slot_zero(origin: Origin) -> None:
    model, refs, _ = _build(origin, [(n, 0) for n in range(1, 11)])
    assert REF_SLOTS == 8
    assert [reference_slot(model, r) for r in refs] == [0, 1, 2, 3, 4, 5, 6, 7, 0, 1]
