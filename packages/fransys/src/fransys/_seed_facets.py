"""The facets a pin source seeds, built from `derive.seed_pins`' rows (model-0281).

Derive holds the rows; this module is the facade's half: ids, keys and origins, nothing decided.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Id, make_id, require_origin
from fransys_model.vocab import (
    AssignedDesignationFacet,
    AssignedUnitTagFacet,
    ReservedDesignationFacet,
)

if TYPE_CHECKING:
    from fransys_model.derive import AssignedSeed, UnitTagSeed
    from fransys_model.derive.numbering_pins import NumberingRetired
    from fransys_model.kernel import Model, Origin
    from fransys_model.vocab import UnitRelease


def assigned_facets(
    model: Model, rows: tuple[AssignedSeed, ...], origins: dict[Id[Any], Origin]
) -> list[AssignedDesignationFacet]:
    """One `assigned_designation` facet per row, its origin the item's."""
    seeded = []
    for row in rows:
        key = (*row.key, "assigned_designation")
        facet_id = make_id(AssignedDesignationFacet, key)
        seeded.append(
            AssignedDesignationFacet(id=facet_id, key=key, subject=row.item, text=row.text)
        )
        origins[facet_id] = require_origin(model.origins, row.item)
    return seeded


def tag_facets(
    model: Model, rows: tuple[UnitTagSeed, ...], origins: dict[Id[Any], Origin]
) -> list[AssignedUnitTagFacet]:
    """One `assigned_unit_tag` facet per row, its origin the instance's."""
    seeded = []
    for row in rows:
        key = (*row.key, "assigned_unit_tag")
        facet_id = make_id(AssignedUnitTagFacet, key)
        seeded.append(
            AssignedUnitTagFacet(id=facet_id, key=key, subject=row.instance, text=row.text)
        )
        origins[facet_id] = require_origin(model.origins, row.instance)
    return seeded


def reserved_facets(
    model: Model,
    release_record: UnitRelease,
    rows: tuple[NumberingRetired, ...],
    origins: dict[Id[Any], Origin],
) -> list[ReservedDesignationFacet]:
    """One `reserved_designation` facet per row, numbered in order, its origin the release's."""
    seeded = []
    for index, row in enumerate(rows):
        key = ("reserved_designation", str(release_record.id), str(index))
        facet_id = make_id(ReservedDesignationFacet, key)
        seeded.append(
            ReservedDesignationFacet(
                id=facet_id,
                key=key,
                subject=release_record.id,
                scope=row.scope,
                code=row.code,
                text=row.text,
            )
        )
        origins[facet_id] = require_origin(model.origins, release_record.id)
    return seeded
