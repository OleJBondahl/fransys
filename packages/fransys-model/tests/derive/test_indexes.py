"""WP11 tests: `derive.indexes` (ROADMAP WP11, design/derive.md)."""

import dataclasses

import pytest
from derive_helpers import add_all

from fransys_model.derive import build_indexes
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab.core import Item

_EXPECTED_INDEXES = frozenset(
    {
        "functions_by_item",
        "ports_by_function",
        "conductors_by_port",
        "nets_by_port",
        "items_by_part",
        "children_by_item",
        "facets_by_subject",
        "placements_by_item",
        "nodes_by_parent",
    }
)


def _mutate(obj, name: str, new_value: object) -> None:
    """Attribute assignment via an unannotated parameter, so `ty` won't statically reject it."""
    setattr(obj, name, new_value)


def _one_item_model(origin: Origin):
    draft = Draft()
    item = Item(
        id=Id(kind="item", value="1" * 32),
        key=("cabinet", "g1"),
        part=None,
        parent=None,
        position=None,
        tag="G1",
        description="24V supply",
    )
    add_all(draft, item, origin=origin)
    return freeze(draft)


def test_indexes_has_every_index_in_design_10(origin: Origin) -> None:
    """`Indexes` declares exactly the fields design/derive.md lists, no more, no fewer."""
    model = _one_item_model(origin)
    idx = build_indexes(model)
    field_names = {f.name for f in dataclasses.fields(idx)}
    assert field_names == _EXPECTED_INDEXES


def test_indexes_result_is_immutable(origin: Origin) -> None:
    """An `Indexes` instance is a frozen dataclass (decision 0012)."""
    model = _one_item_model(origin)
    idx = build_indexes(model)
    with pytest.raises(dataclasses.FrozenInstanceError):
        _mutate(idx, "functions_by_item", frozendict())


def test_build_indexes_caches_on_digest(origin: Origin) -> None:
    """Two calls on models with the same digest return the identical `Indexes` object."""
    model = _one_item_model(origin)
    same_content_model = _one_item_model(origin)
    assert model.digest == same_content_model.digest
    assert build_indexes(model) is build_indexes(same_content_model)
