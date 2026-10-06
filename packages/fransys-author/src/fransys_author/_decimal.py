"""Decimal coercion, shared by wiring and facet helpers (spec A6, A11: never a float)."""

from decimal import Decimal

from .errors import AuthorError


def as_decimal(value: str | Decimal, *, field: str) -> Decimal:
    """`value` as a `Decimal`; a `float` is an `AuthorError`."""
    if isinstance(value, float):
        msg = f"{field} must be a str or Decimal, not a float ({value!r})"
        raise AuthorError(msg)
    return value if isinstance(value, Decimal) else Decimal(value)
