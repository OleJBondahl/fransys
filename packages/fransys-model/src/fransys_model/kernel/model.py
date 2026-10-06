"""Kernel model: the immutable, validated result of `freeze()` (design/kernel-model.md 5.5)."""

import dataclasses
from typing import Any

lazy from .ids import AuthoringKey, Id
lazy from .origin import Origin
lazy from .record import Record

SCHEMA_VERSION = 8
"""The canonical-form version `freeze()` stamps and `from_data` demands (kernel-model.md 5.6)."""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Model:
    """The immutable, validated result of `freeze()`.

    Not a `@value`: it is never nested in a record, and `tables` is keyed by `Id`,
    outside the closed set `@value` enforces on its fields.

    Everything reachable from a `Model` is deeply immutable, checked at freeze, not
    assumed. `tables` stays generic here (`kind -> id -> record`); `vocab` adds typed
    accessors (`items(model)`, `ports(model)`, ...) over it. `digests` holds one digest
    per registered namespace, so a change to `layout.*` records leaves the `core` and
    `facet` digests alone; `digest` combines them (design/kernel-model.md 5.6).
    """

    schema_version: int
    tables: frozendict[str, frozendict[Id[Any], Record]]
    aliases: frozendict[Id[Any], Id[Any]]
    # Not compared: a moved line is not a change to the plant (design/kernel-records.md 5.4), and
    # canonical form does not carry origins, so a reloaded model must equal the original.
    origins: frozendict[Id[Any], Origin] = dataclasses.field(compare=False)
    hashes: frozendict[Id[Any], str]
    digests: frozendict[str, str]
    digest: str

    def origin_of(self, target: Id[Any]) -> Origin | None:
        """Where the record `target` was authored, or `None` (`OriginSource`, kernel-model.md)."""
        return self.origins.get(target)

    def key_of(self, target: Id[Any]) -> AuthoringKey | None:
        """The authoring key of the record `target`, or `None` if no record holds it."""
        table = self.tables.get(target.kind)
        found = None if table is None else table.get(target)
        return None if found is None else found.key
