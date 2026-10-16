"""The table reads the facade needs, as facts: the facade reads no table and no record field.

Each returns what the table walk it replaced gave, in the same order (decision 0221).
"""

from typing import cast

from fransys_model.derive.document_unit import document_unit
from fransys_model.derive.facts.subjects import subject_kind
from fransys_model.derive.facts.units import unit_items, unit_subtree
from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.enums import SubjectKind
from fransys_model.vocab.markings import marking_key
from fransys_model.vocab.revision_text import revision_text
from fransys_model.vocab.tables import (
    documents,
    function_templates,
    functions,
    items,
    parts,
    port_templates,
    ports,
    projects,
    unit_releases,
    units,
)
lazy from fransys_model.derive.rows_baseline import Listing
lazy from fransys_model.kernel import Id, Model, Record
lazy from fransys_model.vocab.core import Function, Item, Unit
lazy from fransys_model.vocab.document import Document
lazy from fransys_model.vocab.templates import Part

__all__ = [
    "document_ids",
    "document_stems",
    "has_documents",
    "has_project",
    "listing_interface",
    "listing_revision_text",
    "part_function_pins",
    "part_records",
    "release_names",
    "subject_part_mpn",
    "unit_chain_below",
    "unit_ids",
    "unit_key",
    "unit_owned_ids",
]


def document_ids(model: Model) -> tuple[Id[Document], ...]:
    """Every document id, in table order."""
    return tuple(documents(model))


def document_stems(model: Model) -> tuple[tuple[Id[Document], str], ...]:
    """Each document id with its name (the second part of its key), in table order."""
    return tuple((one, record.key[1]) for one, record in documents(model).items())


def has_documents(model: Model) -> bool:
    """Whether the model holds a document."""
    return bool(documents(model))


def has_project(model: Model) -> bool:
    """Whether the model holds a project."""
    return bool(projects(model))


def unit_ids(model: Model) -> tuple[Id[Unit], ...]:
    """Every unit id, sorted."""
    return tuple(sorted(units(model)))


def unit_key(model: Model, unit: Id[Unit]) -> tuple[str, ...]:
    """The authoring key of `unit`."""
    return units(model)[unit].key


def unit_chain_below(model: Model, unit: Id[Unit] | None, subject: Id[Unit]) -> list[Id[Unit]]:
    """`subject` and its parents up to, not including, `unit`; `None` goes to the top."""
    chain: list[Id[Unit]] = []
    for link in unit_chain(model, subject):
        if link == unit:
            break
        chain.append(link)
    return chain


def unit_owned_ids(model: Model, unit: Id[Unit]) -> frozenset[Id[Record]]:
    """Every id `unit` owns: its subtree's items, functions, ports, units and its documents."""
    item_ids = unit_items(model, unit)
    function_ids = {fid for fid, fn in functions(model).items() if fn.item in item_ids}
    port_ids = {pid for pid, port in ports(model).items() if port.function in function_ids}
    owned_documents = {i for i, r in documents(model).items() if document_unit(model, r.id) == unit}
    return (
        frozenset(item_ids) | function_ids | port_ids | unit_subtree(model, unit) | owned_documents
    )


def release_names(model: Model) -> tuple[str, ...]:
    """The name of every unit release, in table order."""
    return tuple(release.name for release in unit_releases(model).values())


def subject_part_mpn(model: Model, subject: Id[Record]) -> str | None:
    """The mpn of the part of an item, or of a function's item; `None` when it has no part."""
    if subject_kind(subject) is SubjectKind.ITEM:
        item = items(model)[cast("Id[Item]", subject)]
    else:
        item = items(model)[functions(model)[cast("Id[Function]", subject)].item]
    part = parts(model).get(item.part) if item.part is not None else None
    return part.mpn if part is not None else None


def part_records(model: Model) -> tuple[Part, ...]:
    """Every part record, in table order."""
    return tuple(parts(model).values())


def part_function_pins(model: Model) -> dict[Id[Part], list[tuple[str, list[str]]]]:
    """Each part's function templates and their pin names, both sorted by marking."""
    pins_of: dict[object, list[str]] = {}
    for port in port_templates(model).values():
        pins_of.setdefault(port.function, []).append(port.name)
    for pins in pins_of.values():
        pins.sort(key=marking_key)
    by_part: dict[Id[Part], list[tuple[str, list[str]]]] = {}
    for template in function_templates(model).values():
        by_part.setdefault(template.part, []).append((template.name, pins_of.get(template.id, [])))
    return {part: sorted(fns, key=lambda fn: marking_key(fn[0])) for part, fns in by_part.items()}


def listing_interface(listing: Listing) -> str:
    """The interface text of the unit a baseline listing lists."""
    return listing.unit.interface


def listing_revision_text(listing: Listing) -> str:
    """The `v.r` text of the version and revision of the unit a baseline listing lists."""
    unit = listing.unit
    return revision_text(unit.version, unit.revision)
