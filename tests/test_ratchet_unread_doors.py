"""Ratchet E19: door names with no outside reader and no transitive reader (SURFACE-COHERENCE)."""

import pytest
from gate_scan import check_stock, stock
from surface_census import DOORS, door_census


@pytest.fixture(scope="module")
def rows():
    return door_census()


@pytest.mark.parametrize("door", DOORS)
def test_the_census_walks_every_door(rows, door):
    assert any(row.module == door for row in rows.values()), f"{door}: no rows"


@pytest.mark.private_input  # a private-gate count (R462)
def test_unread_door_names_stay_at_their_stock(rows):
    found = sum(1 for row in rows.values() if row.unread)
    check_stock("unread_doors", found, stock("unread_doors"))
