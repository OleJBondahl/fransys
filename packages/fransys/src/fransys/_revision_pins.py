"""FD5, FD6, UT4: what a pin source says about a unit's items and its direct instances.

An instance is a row of `items` told apart by its key's last segment (`numbering_pins`).
`pipeline` reads the pin source from disk; this module joins it to the model, reading nothing.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import numbering_pins
from fransys_model.derive.numbering_pins import NumberingItem, NumberingPins, unit_relative_key
from fransys_model.kernel import Finding, Id, Severity, make_id, require_origin
from fransys_model.vocab import AssignedUnitTagFacet, items
from fransys_model.vocab import units as units_table

from . import _designation_pins

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from fransys_model.kernel import AuthoringKey, Model, Origin
    from fransys_model.vocab import Unit

NEW_IN_REVISION = "DESIGNATION_NEW_IN_REVISION"


def _instances(model: Model, unit: Id[Unit]) -> dict[AuthoringKey, Id[Unit]]:
    """The instances directly inside `unit`, by their key relative to it."""
    return {
        numbering_pins.unit_position(model, child.id)[0]: child.id
        for child in units_table(model).values()
        if child.parent == unit
    }


def instance_rows(model: Model, unit: Id[Unit]) -> list[NumberingItem]:
    """Each instance directly inside `unit` as a pre-numbering row, tagged or not (as items')."""
    rows = []
    for child in _instances(model, unit).values():
        key, scope, code = numbering_pins.unit_position(model, child)
        rows.append(NumberingItem(key=key, scope=scope, code=code, text="", authored=False))
    return rows


def seed_tags(
    model: Model, unit: Id[Unit], source: NumberingPins, origins: dict[Id[Any], Origin]
) -> list[AssignedUnitTagFacet]:
    """One `facet.assigned_unit_tag` per untagged instance of `unit` that a pin still matches."""
    by_key = _instances(model, unit)
    seeded = []
    for pin in source.items:
        child = by_key.get(pin.key)
        if child is None or pin.authored or units_table(model)[child].tag is not None:
            continue
        if numbering_pins.unit_position(model, child)[1:] != (pin.scope, pin.code):
            continue
        key = (*units_table(model)[child].key, "assigned_unit_tag")
        facet_id = make_id(AssignedUnitTagFacet, key)
        facet = AssignedUnitTagFacet(id=facet_id, key=key, subject=child, text=pin.text)
        origins[facet.id] = require_origin(model.origins, child)
        seeded.append(facet)
    return seeded


def _subjects(model: Model, unit: Id[Unit]) -> dict[AuthoringKey, Id[Any]]:
    """Every item of `unit` and every instance directly inside it, by relative key."""
    found: dict[AuthoringKey, Id[Any]] = {
        unit_relative_key(model, item.id): item.id
        for item in items(model).values()
        if item.unit == unit
    }
    found.update(_instances(model, unit))
    return found


def moved(model: Model, unit: Id[Unit], path: Path, source: NumberingPins) -> list[Finding]:
    """`DESIGNATION_MOVED` (FD6): a pinned item or instance now prints a different own text."""
    moves = _designation_pins.designation_moves(source, numbering_pins.pins(model, unit))
    subjects = _subjects(model, unit)
    where = path / "baseline" / "numbering.json"
    return [
        Finding(
            code="DESIGNATION_MOVED",
            severity=Severity.ERROR,
            subjects=(subjects[move.key],),
            message=(
                f"{'/'.join(move.key)} was pinned to {move.old_text!r} in {where}, "
                f"and now prints {move.new_text!r}"
            ),
        )
        for move in moves
    ]


def new_in_revision(model: Model, unit: Id[Unit], source: NumberingPins) -> list[Finding]:
    """`DESIGNATION_NEW_IN_REVISION` (UT4): a floating item or instance no pin matches, numbered."""
    known = {(row.key, row.scope, row.code) for row in source.items}
    subjects = _subjects(model, unit)
    return [
        Finding(
            code=NEW_IN_REVISION,
            severity=Severity.WARNING,
            subjects=(subjects[row.key],),
            message=f"{'/'.join(row.key)} is new in this revision and takes {row.text!r}",
        )
        for row in numbering_pins.pins(model, unit).items
        if not row.authored and (row.key, row.scope, row.code) not in known
    ]


def new_findings(model: Model, sources: Mapping[Id[Unit], NumberingPins]) -> list[Finding]:
    """`new_in_revision` for every unit that has a pin source (`build(releases=)`)."""
    return [f for unit in sorted(sources) for f in new_in_revision(model, unit, sources[unit])]


def pin_findings(
    model: Model, unit: Id[Unit], source: tuple[Path, NumberingPins] | None
) -> list[Finding]:
    """The release's own pin findings (FD6, UT4), none without a pin source."""
    if source is None:
        return []
    return [*moved(model, unit, *source), *new_in_revision(model, unit, source[1])]


def with_warnings(raw: tuple[Finding, ...], l4: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """`raw` plus the release checks' WARNINGs it lacks: the manifest lists them (UT4)."""
    return (*raw, *(f for f in l4 if f.severity is Severity.WARNING and f not in raw))
