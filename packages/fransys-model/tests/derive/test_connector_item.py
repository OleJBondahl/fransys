"""`connector_item`: the item that owns a connector function."""

import pytest
from roles_plants import roles_plant

from fransys_model.derive import connector_item
from fransys_model.kernel import SchemaError
from fransys_model.vocab.tables import functions, items

MODEL, _IDS = roles_plant()


def test_connector_item_is_the_functions_own_item() -> None:
    """Each function of the plant maps to the item it is stored on."""
    assert all(connector_item(MODEL, f.id) == f.item for f in functions(MODEL).values())


def test_connector_item_rejects_an_unknown_function() -> None:
    """An item id is no function of the model, so it is a `SchemaError`."""
    with pytest.raises(SchemaError):
        connector_item(MODEL, next(iter(items(MODEL))))  # ty: ignore[invalid-argument-type] -- wrong table
