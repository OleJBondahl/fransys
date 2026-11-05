"""`merge()`: combine drafts and models into one `Draft` (design/kernel-model.md 5.7)."""

from typing import TYPE_CHECKING, Any

from .draft import Draft
from .errors import SchemaError
from .model import Model
from .origin import require_origin

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .ids import Id
    from .origin import Origin
    from .record_protocol import Record


def merge(*parts: Draft | Model) -> Draft:
    """Combine `parts` into one new `Draft`, order-independent.

    Same id with identical content deduplicates, keeping the smaller origin; different
    content raises. Aliases of all parts are united; one retired id may not lead to two ids.
    The parts are not changed. Records and aliases are added in `Id` order, so the same error
    escapes in any part order: a record conflict before an alias one, then the smallest id.

    Raises:
        MergeConflictError: two parts declare the same id with different content, naming
            both origins.
        SchemaError: a part is neither a `Draft` nor a `Model`, a `Model` holds a record
            with no origin, or two parts' aliases retire one id in favour of two ids.
    """
    entries: list[tuple[Record, Origin]] = []
    aliases: list[tuple[Id[Any], Id[Any]]] = []
    for part in parts:
        records, found, origins = _unpack(part)
        entries.extend((record, require_origin(origins, record.id)) for record in records)
        aliases.extend(found.items())
    merged = Draft()
    for record, where in sorted(entries, key=_by_id_then_origin):
        merged.add(record, origin=where)
    for old, new in sorted(aliases):
        merged.alias(old, new)
    return merged


def _unpack(part: Draft | Model) -> tuple[Iterable[Record], Mapping[Id[Any], Id[Any]], Mapping[Id[Any], Origin]]:
    if isinstance(part, Draft):
        return part.records(), part.alias_map(), part.origins()
    if isinstance(part, Model):
        return tuple(record for table in part.tables.values() for record in table.values()), part.aliases, part.origins
    msg = f"merge takes a Draft or a Model, not a {type(part).__name__}"
    raise SchemaError(msg, kind="merge")


def _by_id_then_origin(entry: tuple[Record, Origin]) -> tuple[Id[Any], str, int, str]:
    record, where = entry
    return record.id, where.file, where.line, where.note
