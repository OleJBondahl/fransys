"""Kernel identity.

Opaque, deterministic ids and the authoring keys they derive from (design/kernel-records.md 5.2,
decision 0004).
"""

import uuid
from functools import total_ordering
from typing import Any

from .errors import SchemaError
from .record import value
from .registry import register_id

# The structured, front-end-chosen key a record's id derives from. Stable under
# insertion: never a counter, never a positional index the author did not write.
type AuthoringKey = tuple[str, ...]

_SEPARATOR = "\x1f"
# Fixed for good: changing this string changes every id in every model.
_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "schematika-model:id"
)  # predates the rename: seed, never changed (FR2)


@total_ordering
@value
class Id[K]:
    r"""Opaque, deterministic identity for a record of type `K`.

    Not a `str`: `kind` and `value` make `Id[Port]` and `Id[Function]` distinct at
    runtime as well as to `ty`. `value` is
    `uuid5(NAMESPACE, kind + "\x1f" + "\x1f".join(key))`: the same kind and key always
    produce the same id, on every machine. Ids order by `(kind, value)`.
    """

    kind: str
    value: str

    def __post_init__(self) -> None:
        """Refuse what `render_id` could not write and `parse_id` could not read back."""
        if not self.kind or ":" in self.kind or not self.value:
            msg = (
                f"an Id needs a kind without `:` and a value, got {self.kind!r} and {self.value!r}"
            )
            raise SchemaError(msg, kind="id")

    def __lt__(self, other: object) -> bool:
        """Order by `(kind, value)`; `total_ordering` derives the other comparisons."""
        if not isinstance(other, Id):
            return NotImplemented
        return (self.kind, self.value) < (other.kind, other.value)


register_id(Id, AuthoringKey)


def make_id[K](record_type: type[K], key: AuthoringKey) -> Id[K]:
    r"""Derive `record_type`'s id from `key`.

    `record_type` must be a `@record` class itself, not its kind name or an instance, and
    a subclass does not inherit its parent's kind.

    Raises:
        SchemaError: `record_type` is not a `@record` kind, or `key` is not a tuple of
            `str`, is empty, contains an empty segment, a segment holding the `\x1f`
            separator byte, or a lone surrogate (design/kernel-records.md 5.2).
    """
    kind = vars(record_type).get("__kind__") if isinstance(record_type, type) else None
    if kind is None:
        name = getattr(record_type, "__qualname__", repr(record_type))
        msg = f"{name} is not a @record kind"
        raise SchemaError(msg, kind=name)
    # A str or list key would join like a tuple and collide with it, so the type is checked.
    if not isinstance(key, tuple) or not all(isinstance(segment, str) for segment in key):
        msg = f"authoring key {key!r} is not a tuple of str"
        raise SchemaError(msg, kind=kind)
    if not key:
        msg = "authoring key has no segments"
        raise SchemaError(msg, kind=kind)
    for segment in key:
        if not segment:
            msg = f"authoring key {key!r} has an empty segment"
            raise SchemaError(msg, kind=kind)
        if _SEPARATOR in segment:
            msg = f"authoring key segment {segment!r} holds the separator"
            raise SchemaError(msg, kind=kind)
    uuid_name = kind + _SEPARATOR + _SEPARATOR.join(key)
    try:
        digest = uuid.uuid5(_NAMESPACE, uuid_name)
    except UnicodeEncodeError as exc:
        msg = f"authoring key {key!r} is not UTF-8 encodable (lone surrogate)"
        raise SchemaError(msg, kind=kind) from exc
    return Id(kind=kind, value=digest.hex)


def render_id[K](target: Id[K]) -> str:
    """Write `target` as `kind:value`: the only place an `Id` becomes text (kernel-records.md)."""
    return f"{target.kind}:{target.value}"


def parse_id(text: str) -> Id[Any]:
    """Read `kind:value` back: the only place text becomes an `Id`.

    The kind grammar forbids `:`, so the first one is the separator.
    The value is not checked for hex: fixtures build readable ids by hand.
    """
    kind, colon, value_text = text.partition(":")
    if not colon or not kind or not value_text:
        msg = f"{text!r} is not `kind:value`"
        raise SchemaError(msg, kind="id")
    return Id(kind=kind, value=value_text)
