"""WP "drawing text": `derive.drawing_text` (decision model-0032).

Hand-built records only, on the model's synthetic plant: every formatter case and every
branch of every reader (`marker_text`, `page_title`).
"""

from typing import TYPE_CHECKING, Any

import pytest
from derive_helpers import (
    add_all,
    frozen_with_library,
    house_record,
    reference_row,
)
from derive_helpers import (
    control_page as _page,
)
from derive_helpers import (
    house_sheet as _sheet,
)
from derive_helpers import (
    ids as _ids,
)
from derive_helpers import (
    numbered_set as _drawing_set,
)
from derive_helpers import (
    record_key as _key,
)
from derive_helpers import (
    tagged_item as _item,
)

from fransys_model.derive.drawing_text import (
    marker_text,
    position_text,
)
from fransys_model.kernel import Draft, Id, Origin, SchemaError
from fransys_model.layout import (
    LinkMarker,
    MarkerSide,
    ReferenceText,
    Side,
    StarKind,
)
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PortBoundary

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


def _function(new_id: Callable[[str], Id[Any]], *, item: Id[Item], kind: FunctionKind = FunctionKind.COIL) -> Function:
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
        boundary=PortBoundary.GENERIC,
        marking=marking,
    )


def _conductor(new_id: Callable[[str], Id[Any]], *, a: Id[Port], b: Id[Port]) -> Conductor:
    id_ = new_id("conductor")
    return Conductor(id=id_, key=_key(id_), a=a, b=b, kind=ConductorKind.WIRE, carrier=None)


# --------------------------------------------------------------------------------------
# position_text: pure formatter
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


def _star_model(origin: Origin, branch_xs: tuple[int, ...], *, with_rows: bool = True) -> tuple[Any, list[LinkMarker]]:
    """The model and markers (the reference first) of a star whose branches stand at `branch_xs`."""
    new_id = _ids()
    draft = Draft()
    sheet = _sheet(new_id)
    ds = _drawing_set(new_id, number=1)
    page_a, page_b = (_page(new_id, drawing_set=ds.id, number=n, sheet_format=sheet.id) for n in (1, 2))
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
            facing=Side.E,
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
                facing=Side.E,
            )
        )
    rows = [reference_row(m, 1 if m.x < 100 else 8, "A") for m in markers] if with_rows else []
    add_all(draft, sheet, ds, page_a, page_b, item, fn, ref_port, *ports, *markers, *rows, origin=origin)
    return frozen_with_library(draft), markers


def _star_text(origin: Origin, branch_xs: tuple[int, ...], *, with_rows: bool = True) -> str:
    """The reference marker's text for a star whose branches stand at `branch_xs` on one page."""
    model, markers = _star_model(origin, branch_xs, with_rows=with_rows)
    return marker_text(model, markers[0])


def test_marker_text_keeps_two_different_lines(origin: Origin) -> None:
    """Branches in two cells stay two distinct targets: the first and `+1` (model-0139)."""
    assert _star_text(origin, (10, 10, 400)).split("\n") == ["#1-p2:1A +1"]  # first and a count


# `partner_position_text`
# --------------------------------------------------------------------------------------

_NODE_IDS = _ids()
_PATH_CAB: tuple[tuple[Id[Any], str], ...] = ((_NODE_IDS("aspect_node"), "C1"),)


def test_a_position_without_a_cell_names_the_page_alone() -> None:
    refs = house_record(ReferenceText)
    assert position_text(refs, 3, None) == "p3"
    assert position_text(refs, 3, None, "+C1") == "+C1 p3"
    assert position_text(refs, 3, ("1", "A")) == "p3:1A"
    assert position_text(refs, 2, ("4", "A"), "+EXT-M1") == "+EXT-M1 p2:4A"


def test_a_marker_with_no_reference_row_raises(origin: Origin) -> None:
    """The cell is read from the marker's REFERENCE membership row; a missing row is no silent default (R897)."""
    with pytest.raises(SchemaError):
        _star_text(origin, (10,), with_rows=False)


def test_external_frame_title_is_empty_by_default() -> None:
    """The by-others frame carries no text unless a consumer sets one (R2127, el-0127)."""
    from fransys_model.derive.drawing_text import external_frame_title

    assert external_frame_title() == ""
