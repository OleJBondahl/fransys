"""Kernel draft: the mutable collector of records (design/kernel-model.md 5.5)."""

from typing import Any
lazy from collections.abc import Iterable

from .errors import MergeConflict, SchemaError
from .ids import Id
lazy from .ids import AuthoringKey
lazy from .origin import Origin
lazy from .record import Record


class Draft:
    """The only mutable type in the repo. Collects records before `freeze()`.

    Accepts a duplicate `add` of identical content as a no-op; a conflicting `add` under
    the same id raises `MergeConflict` immediately, naming both origins. Nothing here
    depends on the order things were added in: the accessors sort. A draft that raised is
    to be discarded, not repaired.
    """

    def __init__(self) -> None:
        """Start empty."""
        self._records: dict[Id[Any], Record] = {}
        self._origins: dict[Id[Any], Origin] = {}
        self._aliases: dict[Id[Any], Id[Any]] = {}

    def add(self, record: Record, *, origin: Origin) -> None:
        """Add `record`, attributing it to `origin`.

        An identical record already present keeps the smaller origin by
        `(file, line, note)`, so the choice does not depend on the order of the calls.

        Raises:
            SchemaError: `record` is not an instance of a `@record` class, or its id is of
                another kind than its class.
            MergeConflict: `record.id` is already present with different content.
        """
        cls = type(record)
        kind = vars(cls).get("__kind__")
        if kind is None or not isinstance(record.id, Id) or record.id.kind != kind:
            msg = f"{cls.__qualname__} is not a @record instance with an id of its own kind"
            raise SchemaError(msg, kind=cls.__qualname__)
        present = self._records.get(record.id)
        if present is None:
            self._records[record.id] = record
            self._origins[record.id] = origin
        elif present == record:
            self._origins[record.id] = min(self._origins[record.id], origin, key=_origin_order)
        else:
            msg = "two different records share one id"
            raise MergeConflict(
                msg, record_id=record.id, origin_a=self._origins[record.id], origin_b=origin
            )

    def extend(self, records: Iterable[Record], *, origin: Origin) -> None:
        """Add every record in `records`, all attributed to `origin`.

        Not atomic: a conflict leaves the records before it in place.
        """
        for record in records:
            self.add(record, origin=origin)

    def alias(self, old: Id[Any], new: Id[Any]) -> None:
        """Record that `old` has been retired in favour of `new`.

        `freeze()` rewrites a reference to `old` into one to `new`. Saying the same thing
        twice is fine.

        Raises:
            SchemaError: `old` is `new`, they are of different kinds, or `old` is already
                retired in favour of another id.
        """
        if old == new or old.kind != new.kind:
            msg = "an alias must retire an id in favour of a different id of the same kind"
            raise SchemaError(msg, kind=old.kind)
        if self._aliases.setdefault(old, new) != new:
            msg = "an id cannot be retired in favour of two different ids"
            raise SchemaError(msg, kind=old.kind)

    def records(self) -> tuple[Record, ...]:
        """Every record, sorted by id."""
        return tuple(sorted(self._records.values(), key=lambda record: record.id))

    def origins(self) -> frozendict[Id[Any], Origin]:
        """Where each record was authored."""
        return frozendict(self._origins)

    def alias_map(self) -> frozendict[Id[Any], Id[Any]]:
        """Every retired id and the id that replaces it, as authored."""
        return frozendict(self._aliases)

    def origin_of(self, target: Id[Any]) -> Origin | None:
        """Where the record `target` was authored, or `None` (`OriginSource`, kernel-model.md)."""
        return self._origins.get(target)

    def key_of(self, target: Id[Any]) -> AuthoringKey | None:
        """The authoring key of the record `target`, or `None` (`OriginSource`, kernel-model.md)."""
        record = self._records.get(target)
        return None if record is None else record.key

    def record_of(self, target: Id[Any]) -> Record | None:
        """The record under `target`, or `None` (kernel-model.md), like `key_of`, no alias."""
        return self._records.get(target)


def _origin_order(origin: Origin) -> tuple[str, int, str]:
    return origin.file, origin.line, origin.note
