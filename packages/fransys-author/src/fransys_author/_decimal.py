"""Decimal coercion, shared by wiring and facet helpers (never a float)."""

from decimal import Decimal

from .errors import AuthorError

type ProfileNumber = int | Decimal | frozendict[str, int]  # a profile keyword: G, mm or a rank map


def as_decimal(value: str | Decimal, *, field: str) -> Decimal:
    """`value` as a `Decimal`; a `float` is an `AuthorError`."""
    if isinstance(value, float):
        msg = f"{field} must be a str or Decimal, not a float ({value!r})"
        raise AuthorError(msg)
    return value if isinstance(value, Decimal) else Decimal(value)
