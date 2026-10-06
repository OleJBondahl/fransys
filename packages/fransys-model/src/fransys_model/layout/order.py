"""Layout: construction-time normalisation shared by the kinds that hold ordered entries.

Anything ordered in a layout record carries an explicit `index` and is stored sorted by it
(design/layout-namespace.md). Input of the wrong shape is left as it is: `freeze()` reports it with
its field name, so no `TypeError` escapes a constructor.
"""

from itertools import pairwise
from typing import Any, Protocol, cast

from fransys_model.kernel import Id, Record, SchemaError


class Indexed(Protocol):
    """An entry with a place in its record's order."""

    @property
    def index(self) -> int:
        """Where the entry sits; two entries of one record never share one."""
        ...


def holder_of(record: Record) -> Id[Any] | None:
    """The id of the record that refuses, for its error; `None` if it is not even an `Id`."""
    return record.id if type(record.id) is Id else None


def by_index[E: Indexed](
    found: object, entry_type: type[E], *, kind: str, holder: Id[Any] | None
) -> tuple[E, ...] | None:
    """Return `found` sorted by `index`, or `None` if it is not a tuple of `entry_type`.

    Raises `SchemaError` when two entries share an `index`.
    """
    if type(found) is not tuple:
        return None
    if not all(type(entry) is entry_type and type(entry.index) is int for entry in found):
        return None
    ordered = tuple(sorted(cast("tuple[E, ...]", found), key=lambda entry: entry.index))
    for before, after in pairwise(ordered):
        if before.index == after.index:
            msg = f"two entries share the index {after.index}, so their order is undefined"
            raise SchemaError(msg, kind=kind, record_id=holder)
    return ordered
