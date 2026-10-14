"""Which drawn box or line each row of a `ListingDiff` marks (OVERVIEW O19, model-0197).

A row names its subject as the listing prints it. The listing's own text functions are run over
the model, and a row marks what prints the same text; no text is parsed.
"""

from dataclasses import dataclass
from typing import Any

from fransys_model.vocab.membership import unit_own_roots
from fransys_model.vocab.tables import conductors, functions, items, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .baseline_designation import _cross_function_text, _cross_port_text, unit_designation
from .mate_rows import mates
from .overview_levels import level_box, overview_level
from .reports import _conductor_unit
from .rows import Change, DiffMark, LineRef, ListingDiff, OverviewLevel, OverviewLinkKind

__all__ = ["diff_marks"]


def _boxes_of(
    model: Model, unit: Id[Unit] | None, texts: dict[str, list[Id[Any]]], text: str
) -> tuple[Id[Any], ...]:
    """The level boxes holding the items printed as `text`."""
    found = {level_box(model, item, unit) for item in texts.get(text, ())}
    return tuple(sorted((box for box in found if box is not None), key=str))


def _item_texts(model: Model, unit: Id[Unit] | None) -> dict[str, list[Id[Any]]]:
    """Each item of the model by the listing designation it prints in `unit`'s listing."""
    found: dict[str, list[Id[Any]]] = {}
    for item in items(model):
        found.setdefault(unit_designation(model, unit, item), []).append(item)
    return found


def _unit_texts(model: Model, unit: Id[Unit] | None) -> dict[str, list[Id[Any]]]:
    """Each nested unit by the instance text the `units` section prints (its smallest root)."""
    found: dict[str, list[Id[Any]]] = {}
    for record in units(model).values():
        if record.parent == unit and (roots := unit_own_roots(model, record.id)):
            text = min(unit_designation(model, unit, root) for root in roots)
            found.setdefault(text, []).append(record.id)
    return found


def _conductor_lines(
    model: Model, unit: Id[Unit] | None, level: OverviewLevel
) -> dict[tuple[str, ...], list[LineRef]]:
    """The level lines carrying each conductor, by its sorted end texts."""
    found: dict[tuple[str, ...], list[LineRef]] = {}
    for conductor in conductors(model).values():
        if _conductor_unit(model, conductor) != unit:
            continue
        ends = tuple(
            sorted(
                (
                    _cross_port_text(model, unit, conductor.a),
                    _cross_port_text(model, unit, conductor.b),
                )
            )
        )
        found.setdefault(ends, []).extend(
            line.ref for line in level.lines if conductor.id in line.conductors
        )
    return found


def _mate_lines(
    model: Model, unit: Id[Unit] | None, level: OverviewLevel
) -> dict[tuple[str, ...], list[LineRef]]:
    """The level mate lines for each mate, by its sorted end texts."""
    found: dict[tuple[str, ...], list[LineRef]] = {}
    mate_lines = [line.ref for line in level.lines if line.ref.kind is OverviewLinkKind.MATE]
    for row in mates(model):
        ends = tuple(
            sorted(
                (_cross_function_text(model, unit, row.a), _cross_function_text(model, unit, row.b))
            )
        )
        joined = {level_box(model, functions(model)[f].item, unit) for f in (row.a, row.b)}
        found.setdefault(ends, []).extend(ref for ref in mate_lines if {ref.a, ref.b} == joined)
    return found


@dataclass(frozen=True)
class _Texts:
    """What the listing's texts name on one level."""

    items: dict[str, list[Id[Any]]]
    units: dict[str, list[Id[Any]]]
    wires: dict[tuple[str, ...], list[LineRef]]
    mates: dict[tuple[str, ...], list[LineRef]]


def _marked(
    model: Model, unit: Id[Unit] | None, texts: _Texts, change: Change
) -> tuple[tuple[Id[Any], ...], list[LineRef]]:
    """The boxes and lines one change row marks."""
    parts = change.parts
    match change.section:
        case "items":
            return _boxes_of(model, unit, texts.items, parts[0]), []
        case "boundary":
            return _boxes_of(model, unit, texts.items, parts[0].rsplit(":", 1)[0]), []
        case "units":
            return tuple(texts.units.get(parts[0], ())), []
        case "conductors":
            return (), texts.wires.get((parts[0], parts[1]), [])
        case "mates":
            return (), texts.mates.get((parts[0], parts[1]), [])
    return (), []


def diff_marks(model: Model, unit: Id[Unit] | None, diff: ListingDiff) -> tuple[DiffMark, ...]:
    """One `DiffMark` per row of `diff`, on `unit`'s level: the boxes and lines it marks.

    `unit` is the listed unit, `None` for the system. An `items` or `boundary` row marks the box
    holding its item, a `units` row the nested unit's box, a `conductors` row the lines carrying
    that conductor and a `mates` row the mate line between its two boxes. A row of a removed
    thing, or of `nets`, marks nothing: the new model has nothing to point at.
    """
    level = overview_level(model, unit)
    texts = _Texts(
        items=_item_texts(model, unit),
        units=_unit_texts(model, unit),
        wires=_conductor_lines(model, unit, level),
        mates=_mate_lines(model, unit, level),
    )
    marks = []
    for index, change in enumerate(diff.changes):
        boxes, refs = (
            ((), []) if change.change == "removed" else _marked(model, unit, texts, change)
        )
        marks.append(
            DiffMark(
                change=index, status=change.change, boxes=boxes, lines=tuple(dict.fromkeys(refs))
            )
        )
    return tuple(marks)
