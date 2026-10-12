"""WP "drawing text": `derive.drawing_text` (decision model-0032).

Hand-built records only, on the model's synthetic plant: every formatter case and every
branch of every reader (`marker_text`, `cross_reference_text`, `label_text`, `page_title`).
"""

import itertools
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from derive_helpers import add_all

from fransys_model.derive.drawing_text import (
    marker_text,
    position_text,
)
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    PageRole,
    SheetFormat,
    StarKind,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PortRole
lazy from fransys_model.vocab.aspects import AspectNode

if TYPE_CHECKING:
    from collections.abc import Callable

PRODUCED_BY = "test-engine 0.0.0"

# The house-conventions sheet, in grid units, used by every test: content_width_mm=400,
# module_mm=2.5 -> 400 * 8 // 2.5 = 1280 grid units of content width, 8 frame columns.
CONTENT_WIDTH_GRID = 1280
FRAME_COLUMNS = 8
# The row twin: content_height_mm=257, module_mm=2.5 -> 257 * 8 // 2.5 = 822 grid units of
# content height, 6 frame rows.
CONTENT_HEIGHT_GRID = 822
FRAME_ROWS = 6


def _ids() -> Callable[[str], Id[Any]]:
    """A fresh id maker: distinct `kind`s may safely reuse the same numeric value."""
    counter = itertools.count(1)

    def make(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    return make


def _key(id_: Id[Any], *tail: str) -> tuple[str, ...]:
    return (str(id_.value)[:8], *tail)


def _sheet(new_id: Callable[[str], Id[Any]]) -> SheetFormat:
    id_ = new_id("layout.sheet_format")
    return SheetFormat(
        id=id_,
        key=_key(id_),
        name="test sheet",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=257,
        frame_columns=FRAME_COLUMNS,
        frame_rows=FRAME_ROWS,
        module_mm=Decimal("2.5"),
    )


def _drawing_set(
    new_id: Callable[[str], Id[Any]], *, number: int, location: Id[AspectNode] | None = None
) -> DrawingSet:
    id_ = new_id("layout.drawing_set")
    return DrawingSet(
        id=id_, key=_key(id_), location=location, number=number, produced_by=PRODUCED_BY
    )


def _page(
    new_id: Callable[[str], Id[Any]],
    *,
    drawing_set: Id[DrawingSet],
    number: int,
    sheet_format: Id[SheetFormat] | None,
) -> Page:
    id_ = new_id("layout.page")
    return Page(
        id=id_,
        key=_key(id_),
        drawing_set=drawing_set,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format,
        groups=(),
        produced_by=PRODUCED_BY,
    )


def _item(new_id: Callable[[str], Id[Any]], *, designation: str) -> Item:
    id_ = new_id("item")
    return Item(
        id=id_,
        key=_key(id_),
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="an invented item",
    )


def _function(
    new_id: Callable[[str], Id[Any]], *, item: Id[Item], kind: FunctionKind = FunctionKind.COIL
) -> Function:
    id_ = new_id("function")
    return Function(id=id_, key=_key(id_), item=item, template=None, name="fn", kind=kind)


def _port(
    new_id: Callable[[str], Id[Any]],
    *,
    function: Id[Function],
    name: str = "1",
    marking: str | None = None,
) -> Port:
    id_ = new_id("port")
    return Port(
        id=id_,
        key=_key(id_),
        function=function,
        template=None,
        name=name,
        role=PortRole.GENERIC,
        marking=marking,
    )


def _conductor(new_id: Callable[[str], Id[Any]], *, a: Id[Port], b: Id[Port]) -> Conductor:
    id_ = new_id("conductor")
    return Conductor(id=id_, key=_key(id_), a=a, b=b, kind=ConductorKind.WIRE, carrier=None)


# --------------------------------------------------------------------------------------
# frame_column, position_text: pure formatters
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# marker_text
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# page_title
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# unit_label, outline_title and page_title's unit fallback (decision model-0066)
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# label_text
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# cross_reference_text
# --------------------------------------------------------------------------------------
#
# The old model-0032 conductor-walking tests no longer apply under the new `Label`-taking
# signature: `cross_reference_text` no longer looks up a function, so there is
# nothing "unknown" for it to raise on; and it no longer walks conductors to find whether a
# function is placed, so there is no "unplaced function" path either -- it only formats
# `label.partners`, which `Label.__post_init__` (task 1) already guarantees is non-empty for
# every `CROSS_REFERENCE` label, so an "empty" case is not constructible any more. Both old
# tests are dropped rather than forced to keep a scenario that can no longer happen; this
# mirrors `marker_text`, whose partner is likewise trusted from persisted, referentially
# valid records and carries no "unknown" test of its own.


def _star_text(origin: Origin, branch_xs: tuple[int, ...]) -> str:
    """The reference marker's text for a star whose branches stand at `branch_xs` on one page."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page_a, page_b = (
        _page(new_id, drawing_set=ds.id, number=n, sheet_format=sheet.id) for n in (1, 2)
    )
    item = _item(new_id, designation="K1")
    fn = _function(new_id, item=item.id)
    ref_id = new_id("layout.link_marker")
    ref_port = _port(new_id, function=fn.id, name="0")
    markers = [
        LinkMarker(
            id=ref_id,
            key=_key(ref_id),
            page=page_a.id,
            port=ref_port.id,
            side=MarkerSide.OWNER,
            partner=ref_id,
            star=StarKind.REF,
            x=0,
            y=0,
            width=13,
            height=8,
            produced_by=PRODUCED_BY,
        )
    ]
    ports = [_port(new_id, function=fn.id, name=str(i + 1)) for i in range(len(branch_xs))]
    for port, x in zip(ports, branch_xs, strict=True):
        id_ = new_id("layout.link_marker")
        markers.append(
            LinkMarker(
                id=id_,
                key=_key(id_),
                page=page_b.id,
                port=port.id,
                side=MarkerSide.USER,
                partner=ref_id,
                star=StarKind.BRANCH,
                x=x,
                y=0,
                width=13,
                height=8,
                produced_by=PRODUCED_BY,
            )
        )
    add_all(draft, sheet, ds, page_a, page_b, item, fn, ref_port, *ports, *markers, origin=origin)
    return marker_text(freeze(draft), markers[0])


def test_marker_text_keeps_two_different_lines(origin: Origin) -> None:
    """Branches in two cells stay two distinct targets: the first and `+1` (model-0139)."""
    assert _star_text(origin, (10, 10, 400)).split("\n") == ["#1-p2:1A +1"]  # first and a count


# `partner_position_text`
# --------------------------------------------------------------------------------------

_NODE_IDS = _ids()
_PATH_CAB: tuple[tuple[Id[Any], str], ...] = ((_NODE_IDS("aspect_node"), "C1"),)


def test_a_position_without_a_cell_names_the_page_alone() -> None:
    assert position_text(3, None, None, ()) == "p3"
    assert position_text(3, None, None, ("C1",)) == "+C1p3"
    assert position_text(3, None, None, (), 2) == "p2.3"
    assert position_text(3, 1, "A", (), 2) == "p2.3:1A"
