"""The name of a contact-table spot (R339): a table spot's name starts with `table-`."""

__all__ = ["is_table_spot"]

PREFIX = "table-"  # a table spot's name starts so; a label corner is BL, TL, BR or TR


def is_table_spot(name: str) -> bool:
    """True for the spot name of a table annex, false for a designation corner."""
    return name.startswith(PREFIX)
