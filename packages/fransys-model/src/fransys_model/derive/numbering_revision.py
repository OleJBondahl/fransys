"""The findings a pin source gives a revision: moved designations and new floating ones.

Model-0281. `path` is the release folder the pins were read from, a value for the message.
"""

lazy from pathlib import Path

from fransys_model.kernel import AuthoringKey, Finding, Id, Model, Severity
from fransys_model.vocab import ref
from fransys_model.vocab.codes import fix_text
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab.core import Item, Unit

from .numbering_moves import designation_moves
from .numbering_pins import pins
from .numbering_seed import instances
from .unit_relative_key import unit_relative_key
lazy from .rows_baseline import NumberingPins

NEW_IN_REVISION = "DESIGNATION_NEW_IN_REVISION"


def _subjects(model: Model, unit: Id[Unit]) -> dict[AuthoringKey, Id[Item] | Id[Unit]]:
    """Every item of `unit` and every instance directly inside it, by relative key."""
    found: dict[AuthoringKey, Id[Item] | Id[Unit]] = {
        unit_relative_key(model, item.id): item.id
        for item in items(model).values()
        if item.unit == unit
    }
    found.update(instances(model, unit))
    return found


def moved_findings(
    model: Model, unit: Id[Unit], source: NumberingPins, path: Path
) -> list[Finding]:
    """`DESIGNATION_MOVED`: a pinned item or instance now prints a different own text."""
    moves = designation_moves(source, pins(model, unit))
    subjects = _subjects(model, unit)
    where = path / "baseline" / "numbering.json"
    return [
        Finding(
            code="DESIGNATION_MOVED",
            severity=Severity.ERROR,
            subjects=(subjects[move.key],),
            fix=fix_text("DESIGNATION_MOVED", subject=ref(subjects[move.key])),
            message=(
                f"{ref(subjects[move.key])} was pinned to {move.old_text!r} in {where}, "
                f"and now prints {move.new_text!r}"
            ),
        )
        for move in moves
    ]


def new_in_revision_findings(model: Model, unit: Id[Unit], source: NumberingPins) -> list[Finding]:
    """`DESIGNATION_NEW_IN_REVISION`: a floating item or instance no pin matches, numbered."""
    known = {(row.key, row.scope, row.code) for row in source.items}
    subjects = _subjects(model, unit)
    return [
        Finding(
            code=NEW_IN_REVISION,
            severity=Severity.INFO,
            subjects=(subjects[row.key],),
            fix=fix_text(NEW_IN_REVISION),
            message=f"{ref(subjects[row.key])} is new in this revision and takes {row.text!r}",
        )
        for row in pins(model, unit).items
        if not row.authored and (row.key, row.scope, row.code) not in known
    ]


def revision_findings(
    model: Model, unit: Id[Unit], source: NumberingPins, path: Path
) -> list[Finding]:
    """What `source` says about `unit`'s revision: moved designations, then new floating ones."""
    return [
        *moved_findings(model, unit, source, path),
        *new_in_revision_findings(model, unit, source),
    ]


__all__ = ["moved_findings", "new_in_revision_findings", "revision_findings"]
