"""Whether a document's subject has schematic drawings: a location or a unit, not an item."""

lazy from fransys_model.vocab import Document

__all__ = ["has_schematic_subject"]


def has_schematic_subject(record: Document) -> bool:
    """True for a location or unit document; an item or SYSTEM document draws no schematic."""
    return record.location is not None or record.unit is not None or record.unit_name is not None
