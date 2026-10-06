"""Enum-valued arguments (`cls=`, `FunctionKind`, `SignalType`): an unknown one errors (Q5)."""

from enum import Enum

from .errors import AuthorError


def member[E: Enum](cls: type[E], value: str, *, field: str) -> E:
    """`value` as a member of `cls`; an unknown one is an `AuthorError` listing the valid ones."""
    try:
        return cls(value)
    except ValueError:
        valid = ", ".join(member_.value for member_ in cls)
        msg = f"{value!r} is not a valid {field}; valid: {valid}"
        raise AuthorError(msg) from None
