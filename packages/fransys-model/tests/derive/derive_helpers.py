"""Helpers the derive tests import by name; the name is unique across the workspace."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import Origin, evolve, freeze, make_id
from fransys_model.layout import (
    DrawingLibrary,
    PaperChoice,
    SheetFormat,
    a2_sheet_format,
    default_sheet_format,
)
from fransys_model.vocab import PageKind

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Model, Record

_KEY = ("test", "library")
_EM = Decimal(2048)


def add_all(draft: Draft, *records: Record, origin: Origin) -> None:
    """Add every one of `records` to `draft`, all attributed to `origin`."""
    for record in records:
        draft.add(record, origin=origin)


def drawing_library(divisions: int = 8) -> DrawingLibrary:
    """A drawing library record with the bundled library's numbers (a test's own copy)."""
    return DrawingLibrary(
        id=make_id(DrawingLibrary, _KEY),
        key=_KEY,
        module_mm=Decimal("2.5"),
        divisions=divisions,
        wire_pitch=8,
        wire_pitch_fine=4,
        font_family="DejaVu Sans",
        capital_ratio=Decimal(1493) / _EM,
        ascent_ratio=Decimal(1556) / _EM,
        descent_ratio=Decimal(426) / _EM,
        heights=frozendict(
            {
                "smallest": Decimal("1.8"),
                "body": Decimal("2.5"),
                "heading_2": Decimal("3.5"),
                "heading_1": Decimal(5),
            }
        ),
    )


def paper_records() -> tuple[SheetFormat, SheetFormat, PaperChoice]:
    """The paper records the facade writes: A3 by default, the block diagram on A2 (stock)."""
    a3, a2 = default_sheet_format(), a2_sheet_format()
    key = ("test", "paper")
    by_kind = frozendict({PageKind.BLOCK_DIAGRAM.value: a2.id})
    return (
        a3,
        a2,
        PaperChoice(id=make_id(PaperChoice, key), key=key, default=a3.id, by_kind=by_kind),
    )


def with_library(model: Model, divisions: int = 8) -> Model:
    """`model` with a drawing library record, as the facade writes one."""
    origin = Origin(file="derive_helpers.py", line=0, note="test library")
    return evolve(model, put=(drawing_library(divisions), *paper_records()), origin=origin)


def frozen_with_library(draft: Draft, divisions: int = 8) -> Model:
    """`draft` frozen, with a drawing library record."""
    return with_library(freeze(draft), divisions)
