"""Reads for the per-profile runs (model-0192): which units draw with a profile of their own."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read import reading
from fransys_layout.engines.schematic.read.units import function_unit
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import layout_of
from fransys_model.vocab.tables import conductors, functions, items, ports
from fransys_model.vocab.tables import units as units_table

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model


def profile_classes(model: Model, drawn: frozenset[Id[Any]]) -> tuple[tuple[Id[Any], ...], ...]:
    """The units, drawn or authoring a profile, whose profile is not the top's, by equal profile.

    Each group holds the units of one profile and sheet, sorted; the groups are in unit order.
    """
    authored = {one.unit for one in layout_of(model, ModelProfile).values()}
    top = reading.profile_and_sheet(model)
    groups: list[tuple[tuple[Any, Id[Any] | None], list[Id[Any]]]] = []
    for unit in sorted(unit for unit in (drawn | authored) if unit is not None):
        profile, _, sheet = reading.profile_and_sheet(model, unit)
        if (profile, sheet) == (top[0], top[2]):
            continue
        for known, members in groups:
            if known == (profile, sheet):
                members.append(unit)
                break
        else:
            groups.append(((profile, sheet), [unit]))
    return tuple(tuple(members) for _, members in groups)


def unit_ranks(model: Model) -> dict[Id[Any], int]:
    """The place of each unit in drawing set order: after the top design's sets, which are 0."""
    order = {info.unit: (info.order, info.unit) for info in reading.unit_infos(model)}
    return {unit: i + 1 for i, unit in enumerate(sorted(order, key=order.__getitem__))}


def _subject_unit(model: Model, subject: Id[Any]) -> Id[Any] | None:
    """The unit a finding's subject belongs to: a unit, an item, a function or a port."""
    if subject in units_table(model):
        return subject
    if subject in items(model):
        return items(model)[subject].unit
    if subject in conductors(model):
        subject = conductors(model)[subject].a
    if subject in ports(model):
        subject = ports(model)[subject].function
    return function_unit(model, subject) if subject in functions(model) else None


def finding_unit(model: Model, finding: Finding) -> Id[Any] | None:
    """The one unit `finding`'s subjects belong to, or `None` (the top run's).

    A subject that is no unit's (a net, a group) does not count; two units, or none, give `None`.
    """
    found = {_subject_unit(model, subject) for subject in finding.subjects} - {None}
    return next(iter(found)) if len(found) == 1 else None
