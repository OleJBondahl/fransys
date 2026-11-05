"""Helpers the derive tests import by name; the name is unique across the workspace."""

import itertools
import tomllib
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from library_records import paper_records

from fransys_model.kernel import Id, Origin, evolve, freeze, make_id, render_id
from fransys_model.layout import (
    DrawingLibrary,
    DrawingSet,
    FrameCell,
    LinkMarker,
    Membership,
    Page,
    PageRole,
    SheetFormat,
    Shown,
)
from fransys_model.layout import house_records as house_records_of
from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_model.kernel import Draft, Model, Record

_KEY = ("test", "library")
_EM = Decimal(2048)
_HEIGHTS = ("1", "1.8", "2", "2.2", "2.5", "3", "3.2", "3.5", "4", "5", "6")


def add_all(draft: Draft, *records: Record, origin: Origin) -> None:
    """Add every one of `records` to `draft`, all attributed to `origin`."""
    for record in records:
        draft.add(record, origin=origin)


def drawing_library(divisions: int = 8, extra_ems: Mapping[str, Decimal] | None = None) -> DrawingLibrary:
    """A drawing library record with the bundled library's numbers (a test's own copy)."""
    return DrawingLibrary(
        id=make_id(DrawingLibrary, _KEY),
        key=_KEY,
        module_mm=Decimal("2.5"),
        divisions=divisions,
        wire_pitch=8,
        wire_pitch_fine=4,
        font_family="DejaVu Sans",
        ascent_ratio=Decimal(1556) / _EM,
        descent_ratio=Decimal(426) / _EM,
        ems=frozendict({h: Decimal(h) * _EM / 1493 for h in _HEIGHTS} | dict(extra_ems or {})),
        lines=frozendict({"normal": Decimal("0.25"), "thick": Decimal("0.5"), "rule": Decimal("0.18")}),
        heights=frozendict(
            {
                "smallest": Decimal("1.8"),
                "body": Decimal("2.5"),
                "heading_2": Decimal("3.5"),
                "heading_1": Decimal(5),
            }
        ),
    )


def with_library(model: Model, divisions: int = 8, extra_ems: Mapping[str, Decimal] | None = None) -> Model:
    """`model` with a drawing library record, as the facade writes one."""
    origin = Origin(file="derive_helpers.py", line=0, note="test library")
    return evolve(
        model,
        put=(drawing_library(divisions, extra_ems), *paper_records(), *house_records()),
        origin=origin,
    )


def with_house(model: Model) -> Model:
    """`model` with the house text records only, as the facade writes them."""
    origin = Origin(file="derive_helpers.py", line=0, note="test house records")
    return evolve(model, put=house_records(), origin=origin)


def frozen_with_library(draft: Draft, divisions: int = 8, extra_ems: Mapping[str, Decimal] | None = None) -> Model:
    """`draft` frozen, with a drawing library record."""
    return with_library(freeze(draft), divisions, extra_ems)


def house_record[R: Record](kind: type[R]) -> R:
    """The house text record of type `kind`, as `house_records` builds it."""
    return next(r for r in house_records() if isinstance(r, kind))


def house_records() -> tuple[Record, ...]:
    """The house text records of `settings.toml`, built by the model's builders."""
    path = Path(__file__).parents[3] / "fransys" / "src" / "fransys" / "settings.toml"
    t = tomllib.loads(path.read_text(encoding="utf-8"))
    t["profile"] = tomllib.loads(path.parents[3].joinpath("fransys-layout/src/fransys_layout/layout.toml").read_text(encoding="utf-8"))["profile"]
    return house_records_of(t)


def ids() -> Callable[[str], Id[Any]]:
    """A fresh id maker: distinct `kind`s may safely reuse the same numeric value."""
    counter = itertools.count(1)

    def make(kind: str) -> Id[Any]:
        return Id(kind=kind, value=f"{next(counter):032x}")

    return make


def record_key(id_: Id[Any], *tail: str) -> tuple[str, ...]:
    return (str(id_.value)[:8], *tail)


def house_sheet(new_id: Callable[[str], Id[Any]]) -> SheetFormat:
    """The house-conventions sheet: 400 x 257 mm content, 8 frame columns, 6 frame rows, module 2.5 mm."""
    id_ = new_id("layout.sheet_format")
    return SheetFormat(
        id=id_,
        key=record_key(id_),
        name="test sheet",
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


def numbered_set(new_id: Callable[[str], Id[Any]], *, number: int, location: Id[Any] | None = None) -> DrawingSet:
    id_ = new_id("layout.drawing_set")
    return DrawingSet(id=id_, key=record_key(id_), location=location, number=number, produced_by="test-engine 0.0.0")


def control_page(
    new_id: Callable[[str], Id[Any]],
    *,
    drawing_set: Id[DrawingSet],
    number: int,
    sheet_format: Id[SheetFormat] | None,
) -> Page:
    id_ = new_id("layout.page")
    return Page(
        id=id_,
        key=record_key(id_),
        drawing_set=drawing_set,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format,
        groups=(),
        produced_by="test-engine 0.0.0",
    )


def tagged_item(new_id: Callable[[str], Id[Any]], *, designation: str) -> Item:
    id_ = new_id("item")
    return Item(
        id=id_,
        key=record_key(id_),
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="an invented item",
    )


def numbered_drawing_set(unit: Id[Any], number: int) -> DrawingSet:
    key = ("drawing_set", str(number))
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, unit=unit, number=number,
        produced_by="test",
    )  # fmt: skip


def numbered_page(drawing_set: DrawingSet, number: int) -> Page:
    key = ("page", f"{drawing_set.number}.{number}")
    return Page(
        id=make_id(Page, key), key=key, drawing_set=drawing_set.id, number=number,
        role=PageRole.CONTROL, sheet_format=None, groups=(), produced_by="test",
    )  # fmt: skip


def reference_row(marker: LinkMarker, column: int, row: str) -> Membership:
    """The REFERENCE membership row a core layout writes for `marker`, in cell (`column`, `row`)."""
    key = ("test", "membership", "ref", render_id(marker.id), render_id(marker.port), render_id(marker.page))
    return Membership(
        id=make_id(Membership, key),
        key=key,
        page=marker.page,
        sheet=None,
        function=None,
        port=marker.port,
        conductor=None,
        item=None,
        rank=0,
        shown=Shown.REFERENCE,
        cell=FrameCell(column=column, row=row),
        produced_by="test-engine 0.0.0",
    )
