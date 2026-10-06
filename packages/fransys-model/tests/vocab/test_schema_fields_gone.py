"""Schema version 2 (spec 2026-09-26-model-schema, SC4): fields that were removed stay removed.

One `(record kind, field name)` pair per removed field, read from the registry: the class
`lookup_kind` returns and its dataclass fields, never the source text. Each part of the schema
work appends its own pairs.
"""

import pytest

import fransys_model.vocab  # noqa: F401 -- registers every record kind
from fransys_model.kernel.registry import lookup_kind
from fransys_model.kernel.schema import fields_of

REMOVED_FIELDS = [
    ("conductor", "net"),
    ("facet.cable_product", "core_count"),
    ("facet.core", "colour"),
    ("project", "revision_date"),
    ("unit", "name"),
    ("unit", "revision"),
    ("unit", "interface"),
    ("unit", "title"),
    ("unit", "number"),
    ("revision", "unit"),
]


def field_names(kind: str) -> set[str]:
    """The names of every field the registry holds for `kind`."""
    return {field.name for field in fields_of(lookup_kind(kind))}


@pytest.mark.parametrize(("kind", "name"), REMOVED_FIELDS)
def test_a_removed_field_is_not_registered(kind: str, name: str) -> None:
    """SC4: no field named in the spec's removals exists on its kind."""
    assert name not in field_names(kind)


def test_the_helper_finds_a_field_that_does_exist() -> None:
    """Can fail: if `field_names` read nothing, every removal test above would pass vacuously."""
    assert "carrier" in field_names("conductor")
    assert "net" in field_names("layout.route")
