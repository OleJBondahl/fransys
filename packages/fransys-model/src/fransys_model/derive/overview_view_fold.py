"""A folded level's view rows, and the system level's two folds (O3, O3b, O9; model-0202).

A folded stub lists its members in its box (O14). The location fold has a box per top place; the
field fold puts each unit's field devices in one box beside it.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.house_settings import stub_text_of
from fransys_model.layout import BoxKey, OverviewRef, OverviewRefKind
lazy from fransys_model.kernel import Model

from .overview_levels import level_box_lines
from .overview_text import (
    overview_field_join_text,
    overview_fold_line_text,
    overview_location_line_text,
    overview_member_text,
)
from .overview_view_plain import shared_rows, stub_rows
from .rows_overview_view import Rows, ViewBox, ViewLine, ViewMember

if TYPE_CHECKING:
    from .rows_overview import FieldFold, FoldLevel, FoldLine, LocationFold

__all__ = ["field_rows", "fold_rows", "location_rows"]

_UNIT = OverviewRefKind.UNIT


def _line(line: FoldLine) -> ViewLine:
    """A line of the level: its cable when it stands for one and passes no strip."""
    one = line.vias[0] if len(line.vias) == 1 and line.strip is None else None
    return ViewLine(
        a=BoxKey(ref=line.a),
        b=BoxKey(ref=line.b),
        kind=line.kind.value,
        via=one,
        strip=line.strip,
        text=overview_fold_line_text(line),
    )


def fold_rows(model: Model, level: FoldLevel) -> Rows:
    """The folded level's boxes then its stub boxes, its lines then its stub lines."""
    boxes = tuple(
        ViewBox(key=BoxKey(ref=b.key), lines=b.lines, dashed=b.dashed) for b in level.boxes
    )
    lines = tuple(_line(line) for line in level.lines)
    shared = {(w.stub.box, w.stub.end) for w in level.wires}
    own = [s for s in level.stubs if (s.box, s.end) not in shared]
    placed = [(stub.box, stub) for stub in own]
    stub_boxes, stub_lines = stub_rows(model, level.unit, placed)
    hung = [(w.stub.box, w.stub) for w in level.wires]
    more_boxes, more_lines = shared_rows(
        model, level.unit, hung, [(w.part.box, w.part) for w in level.wires]
    )
    return (*boxes, *stub_boxes, *more_boxes), (*lines, *stub_lines, *more_lines)


def location_rows(model: Model, fold: LocationFold) -> Rows:
    """One box per top place, one line per pair of places that share cables."""
    refs = {b.place: OverviewRef(kind=OverviewRefKind.PLACE, node=b.place) for b in fold.boxes}
    boxes = tuple(
        ViewBox(key=BoxKey(ref=refs[b.place]), lines=b.lines, dashed=False) for b in fold.boxes
    )
    lines = tuple(
        ViewLine(
            a=BoxKey(ref=refs[line.a]),
            b=BoxKey(ref=refs[line.b]),
            kind="cable",
            via=line.cables[0] if len(line.cables) == 1 else None,
            strip=None,
            text=overview_location_line_text(model, line),
        )
        for line in fold.lines
    )
    return boxes, lines


def _field_ref(fold: FieldFold) -> OverviewRef:
    return OverviewRef(kind=OverviewRefKind.FIELDS, unit=fold.unit)


def _joins(model: Model, fold: FieldFold) -> tuple[ViewLine, ...]:
    """The fold's lifted lines to its unit, one per kind, text from derive."""
    a = BoxKey(ref=_field_ref(fold))
    b = BoxKey(ref=OverviewRef(kind=_UNIT, unit=fold.unit))
    return tuple(
        ViewLine(
            a=a,
            b=b,
            kind=join.kind.value,
            via=join.cables[0] if len(join.cables) == 1 else None,
            strip=None,
            text=overview_field_join_text(model, join),
        )
        for join in fold.joins
    )


def _members(model: Model, plain: Rows, fold: FieldFold) -> tuple[ViewMember, ...]:
    """The fold's devices as member rows: each device's box text and the text of its lines.

    A device wired by loose wires has no box in `plain`, so its text is `level_box_lines`.
    """
    rows = []
    for d in fold.devices:
        ref = OverviewRef(kind=OverviewRefKind.ITEM, item=d)
        lines = level_box_lines(model, d, None)
        held = [ln.text for ln in plain[1] if BoxKey(ref=ref) in (ln.a, ln.b)]
        rows.append(
            ViewMember(
                ref=ref,
                lines=lines,
                text=overview_member_text(
                    stub_text_of(model), lines, ", ".join(dict.fromkeys(held))
                ),
            )
        )
    return tuple(rows)


def field_rows(model: Model, plain: Rows, folds: tuple[FieldFold, ...]) -> Rows:
    """The system `plain` rows with each unit's field devices in one box with its member rows."""
    boxes, lines = plain
    onto = {
        BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=d)) for f in folds for d in f.devices
    }
    made = tuple(
        ViewBox(
            key=BoxKey(ref=_field_ref(f)),
            lines=f.lines,
            dashed=False,
            members=_members(model, plain, f),
        )
        for f in folds
    )
    kept = tuple(b for b in boxes if b.key not in onto)
    left = tuple(line for line in lines if not {line.a, line.b} & onto)
    return (*kept, *made), (*left, *(j for f in folds for j in _joins(model, f)))
