"""Authored layout kinds."""

import pytest

from fransys_model.kernel import Id, SchemaError
from fransys_model.layout import Chain, ChainEntry, OrderHint


def _chain(*entries: ChainEntry) -> Chain:
    return Chain(
        id=Id(kind="layout.chain", value="1" * 32),
        key=("examples", "layout", "pump1", "power"),
        entries=entries,
    )


def test_order_hint_between_a_group_and_itself_is_a_schema_error() -> None:
    """`before == after` orders nothing, so construction raises."""
    group = Id(kind="aspect_node", value="3" * 32)
    with pytest.raises(SchemaError):
        OrderHint(
            id=Id(kind="layout.order_hint", value="4" * 32),
            key=("examples", "layout", "order"),
            before=group,
            after=group,
        )
