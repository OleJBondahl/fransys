"""The manifest facts a release takes from the model, with no designation text (model-0267)."""

import hashlib

from fransys_model.vocab.membership import unit_items, unit_subtree
from fransys_model.vocab.tables import items, part_libraries, parts, projects, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from . import baseline
from .release_identity import release_identity
from .revisions import current_revision
from .rows_baseline import ManifestHistory, ManifestLibrary, ManifestNested, ManifestRows
from .unit_release import unit_release

__all__ = ["manifest_rows", "nested_units", "rebaseline_subjects"]


def nested_units(model: Model, unit: Id[Unit] | None) -> tuple[Id[Unit], ...]:
    """Every unit nested in `unit`'s subtree, sorted; `None` is every unit of the model."""
    if unit is None:
        return tuple(sorted(units(model)))
    return tuple(sorted(unit_subtree(model, unit) - {unit}))


def rebaseline_subjects(model: Model, unit: Id[Unit] | None) -> tuple[Id[Unit] | None, ...]:
    """`unit` and every unit below it, deepest first, then the system; `None` covers the model.

    A deeper unit has a longer key, so a container never precedes a unit it nests. The system
    (`None` in the tuple) is last and only when `unit` is `None` and the model holds a project.
    """
    members = nested_units(model, None) if unit is None else (unit, *nested_units(model, unit))
    ordered = sorted(members, key=lambda u: (-len(units(model)[u].key), u))
    return (*ordered, *((None,) if unit is None and projects(model) else ()))


def _nested(model: Model, unit: Id[Unit] | None) -> tuple[ManifestNested, ...]:
    """One row per nested release and listing digest: instances of one release give one row."""
    found = set()
    for nested_id in nested_units(model, unit):
        release = unit_release(model, nested_id)
        listing_text = baseline.dumps(baseline.listing(model, nested_id))
        digest = hashlib.sha256(listing_text.encode("utf-8")).hexdigest()
        found.add(
            ManifestNested(
                name=release.name,
                version=release.version,
                revision=release.revision,
                listing_digest=digest,
            )
        )
    return tuple(sorted(found, key=lambda r: (r.name, r.version, r.revision, r.listing_digest)))


def _libraries(model: Model, unit: Id[Unit] | None) -> tuple[ManifestLibrary, ...]:
    """The distinct part libraries behind `unit`'s items (`None`: every item), sorted.

    A unit uses its whole subtree (`unit_items`), broader than the listing.
    """
    all_items = items(model)
    item_ids = all_items.keys() if unit is None else unit_items(model, unit)
    all_parts, all_libraries = parts(model), part_libraries(model)
    part_ids = {part for i in item_ids if (part := all_items[i].part) is not None}
    library_ids = {lib for p in part_ids if (lib := all_parts[p].library) is not None}
    found = {(all_libraries[i].name, all_libraries[i].version) for i in library_ids}
    return tuple(ManifestLibrary(name=name, version=version) for name, version in sorted(found))


def _history(model: Model, unit: Id[Unit] | None) -> ManifestHistory | None:
    release_id = None if unit is None else unit_release(model, unit).id
    entry = current_revision(model, release=release_id)
    if entry is None:
        return None
    return ManifestHistory(
        date=entry.date,
        text=entry.text,
        created=entry.created,
        checked=entry.checked,
        approved=entry.approved,
    )


def manifest_rows(model: Model, unit: Id[Unit] | None) -> ManifestRows:
    """The identity, history, part libraries and nested releases of `unit`'s manifest.

    `unit=None` is the system. Each nested row carries the sha256 of the nested listing's
    canonical text, hashed once here. Warning texts and package versions stay with the facade.
    """
    return ManifestRows(
        identity=release_identity(model, unit),
        entry=_history(model, unit),
        part_libraries=_libraries(model, unit),
        nested=_nested(model, unit),
    )
