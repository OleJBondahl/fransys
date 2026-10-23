"""The `Record` protocol and `key_text`, in their own module so its annotations import at runtime.

`ids` and `values` import `record`, so `record` cannot import them; this module can, which keeps
`inspect.signature` and `get_type_hints` working on `Record` without an import cycle.
"""

from typing import Any, Protocol

lazy from .ids import AuthoringKey, Id
lazy from .values import Value


class Record(Protocol):
    """Structural stand-in for any `@record`-decorated instance: it has `id`, `key`, `ext`.

    Members are read-only properties so a concrete `id: Id[Item]` matches covariantly;
    plain attribute members are invariant and reject every real record.
    """

    @property
    def id(self) -> Id[Any]:
        """The record's primary key."""
        ...

    @property
    def key(self) -> AuthoringKey:
        """The authoring key the id was derived from."""
        ...

    @property
    def ext(self) -> frozendict[str, Value]:
        """Typed-leaf escape hatch for facts not yet modelled."""
        ...


def key_text(record: Record) -> str:
    """Join a record's authoring key with `/`: the one text of a record's key in a message."""
    return "/".join(record.key)
