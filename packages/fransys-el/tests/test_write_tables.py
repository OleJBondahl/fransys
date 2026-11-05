"""A contact-table spot is named apart from a designation corner (R339)."""

from fransys_el.placement_tables import is_table_spot


def test_only_a_table_spot_is_a_table_spot() -> None:
    assert is_table_spot("table-BR")
    assert not any(is_table_spot(c) for c in ("TL", "TR", "BL", "BR"))
