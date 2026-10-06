"""UNIT-TAGS UT3: number each unit instance that has no tag, from its release's `class_code`."""

import dataclasses
from collections.abc import Callable

from fransys_model.derive.designation import designating_ancestors, own_designation_or_none
from fransys_model.derive.instance_tag import unit_tag
from fransys_model.derive.lookups import terminal_items
from fransys_model.derive.unit_release import unit_release
from fransys_model.kernel import Finding, Id, Model, Severity, evolve, make_id
from fransys_model.kernel.origin import require_origin
from fransys_model.vocab.facets.assigned_unit_tag import AssignedUnitTagFacet
from fransys_model.vocab.tables import items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.vocab.core import Unit

type Reserved = Callable[..., frozenset[str]]


def _item_texts(model: Model, parent: Id[Unit] | None) -> set[str]:
    """Own texts of the items in `parent`'s top group (no designating ancestor), terminals out."""
    terminals = terminal_items(model)
    found = set()
    for item in items(model).values():
        if item.unit != parent or item.id in terminals or designating_ancestors(model, item.id):
            continue
        if (text := own_designation_or_none(model, item)) is not None:
            found.add(text)
    return found


def instance_tags_in(model: Model, parent: Id[Unit] | None) -> set[str]:
    """The tags, written or assigned, of the instances directly inside `parent` (UT3, UT4)."""
    siblings = (u.id for u in units_table(model).values() if u.parent == parent)
    return {tag for unit in siblings if (tag := unit_tag(model, unit)) is not None}


def _taken(model: Model, parent: Id[Unit] | None, reserved: Reserved) -> set[str]:
    """Every text already used in `parent`'s top group: item texts, instance tags, reserved ones."""
    return (
        _item_texts(model, parent) | instance_tags_in(model, parent) | reserved(model, parent, None)
    )


def _floating(model: Model) -> list[Unit]:
    """The instances with no tag, written or assigned, whose release has a `class_code`."""
    found = [
        unit
        for unit in units_table(model).values()
        if unit_tag(model, unit.id) is None and unit_release(model, unit.id).class_code
    ]
    return sorted(found, key=lambda unit: (unit.key, unit.id))


def _facets(model: Model, reserved: Reserved) -> list[AssignedUnitTagFacet]:
    taken: dict[Id[Unit] | None, set[str]] = {}
    facets = []
    for unit in _floating(model):
        used = taken.setdefault(unit.parent, _taken(model, unit.parent, reserved))
        code = unit_release(model, unit.id).class_code
        n = 1
        while f"{code}{n}" in used:
            n += 1
        used.add(f"{code}{n}")
        key = (*unit.key, "assigned_unit_tag")
        facet_id = make_id(AssignedUnitTagFacet, key)
        facets.append(
            AssignedUnitTagFacet(id=facet_id, key=key, subject=unit.id, text=f"{code}{n}")
        )
    return facets


def number_unit_tags(model: Model, reserved: Reserved) -> Model:
    """`model` with a `facet.assigned_unit_tag` on each floating instance (`reserved` is FD5's)."""
    # Runs after the items, so their assigned texts count as taken (model-0044).
    facets = _facets(model, reserved)
    if not facets:
        return model
    authored = {facet.id: require_origin(model.origins, facet.subject) for facet in facets}
    evolved = evolve(model, put=facets, origin=authored[facets[0].id])
    origins = type(evolved.origins)({**evolved.origins, **authored})
    return dataclasses.replace(evolved, origins=origins)


def unit_tag_duplicates(model: Model, code: str) -> list[Finding]:
    """One finding per instance whose tag another instance under the same parent also has (UD1)."""
    groups: dict[tuple[Id[Unit] | None, str], list[Unit]] = {}
    for unit in units_table(model).values():
        if (tag := unit_tag(model, unit.id)) is not None:
            groups.setdefault((unit.parent, tag), []).append(unit)
    return [
        Finding(
            code=code,
            severity=Severity.ERROR,
            subjects=(unit.id,),
            message=f"unit instance {'/'.join(unit.key)} has the tag {tag!r}, "
            "which another instance under the same parent has too",
        )
        for (_, tag), same in groups.items()
        if len(same) > 1
        for unit in same
    ]
