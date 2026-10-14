"""The model thing each `Change.subject` of a listing names: `change_subjects`.

It is the inverse of the listing's own subject texts, built from the same functions, so a
renderer never parses a subject text to find the item, unit, conductor or function it names.
"""

from typing import Any

from fransys_model.vocab.membership import is_sole_unit_root, unit_own_roots
from fransys_model.vocab.tables import boundaries, conductors, functions, items, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .baseline_designation import _cross_port_text, unit_designation
from .baseline_diff_units import unit_subject_text
from .baseline_listing import _listing_unit
from .lone_cable import lone_cable
from .reports import _conductor_unit
from .unit_release import unit_release

Subjects = dict[tuple[str, str], "Id[Any]"]


def _item_subjects(model: Model, unit: Id[Unit] | None, whole: str) -> Subjects:
    found: Subjects = {}
    for item in items(model).values():
        if item.unit != unit or lone_cable(model, item.id) is not None:
            continue
        text = "" if is_sole_unit_root(model, item.id) else unit_designation(model, unit, item.id)
        found.setdefault(("items", text or whole), item.id)
    return found


def _unit_subjects(model: Model, unit: Id[Unit] | None) -> Subjects:
    found: Subjects = {}
    for record in units(model).values():
        if record.parent != unit:
            continue
        instance = min(
            unit_designation(model, unit, root) for root in unit_own_roots(model, record.id)
        )
        found.setdefault(("units", f"{unit_release(model, record.id).name} {instance}"), record.id)
    return found


def _wire_subjects(model: Model, unit: Id[Unit] | None) -> Subjects:
    found: Subjects = {}
    for record in boundaries(model).values():
        if record.unit == unit:
            fn = functions(model)[record.function]
            text = f"{unit_designation(model, unit, fn.item)}:{fn.name}"
            found.setdefault(("boundary", text), fn.id)
    for conductor in conductors(model).values():
        if _conductor_unit(model, conductor) == unit:
            a_text, b_text = sorted(
                (
                    _cross_port_text(model, unit, conductor.a),
                    _cross_port_text(model, unit, conductor.b),
                )
            )
            found.setdefault(("conductors", f"{a_text} {b_text}"), conductor.id)
    return found


def change_subjects(model: Model, unit: Id[Unit] | None = None) -> Subjects:
    """The `Id` each `(section, subject)` of `listing(model, unit)`'s diff rows names.

    Sections `items`, `units`, `boundary` (the boundary function) and `conductors`; a row of any
    other section, or of a thing the model no longer holds, has no entry. Two things that share a
    subject text keep the first. Pure.
    """
    whole = unit_subject_text(_listing_unit(model, unit))
    return {
        **_item_subjects(model, unit, whole),
        **_unit_subjects(model, unit),
        **_wire_subjects(model, unit),
    }
