"""The one text order: digit runs by value, so `-X2` stands before `-X10` (NUMBER-SORT K7)."""

import re
lazy from collections.abc import Iterable

from .ids import Id, render_id

__all__ = ["NaturalKey", "canonical", "natural_join", "natural_key", "natural_sorted"]

_RUN = re.compile(r"\d+|\D+")

type NaturalKey = tuple[tuple[tuple[int, int, str], ...], str]


def _token(run: str) -> tuple[int, int, str]:
    """A decimal run sorts by value, any other run as text after every number."""
    return (0, int(run), "") if run.isdecimal() else (1, 0, run)


def natural_key(text: str) -> NaturalKey:
    """Sort key of a printed text: digit runs by value, so `-W2` sorts before `-W10`.

    Text runs compare as strings, case-sensitively, and sort after numbers. The whole text is the
    last tie, so the key is total: two texts have equal keys only when they are equal, and `X01`
    sorts before `X1`.
    """
    return tuple(_token(run) for run in _RUN.findall(text)), text


def natural_sorted(texts: Iterable[str]) -> list[str]:
    """`texts` in `natural_key` order."""
    return sorted(texts, key=natural_key)


def natural_join(texts: Iterable[str]) -> str:
    """`texts` in `natural_key` order, joined with `, `: the one spelling of a printed list."""
    return ", ".join(natural_sorted(texts))


def canonical[T](ids: Iterable[Id[T]]) -> tuple[Id[T], ...]:
    """`ids` in the one Id order, for stored forms, digests and diffs, where the Id is its text.

    The order is `natural_key` of each id's `kind:value` text and does not depend on the order
    the ids arrive in. It takes no key: a reader's order is a `fransys_model.derive.order` key.
    """
    return tuple(sorted(ids, key=lambda one: natural_key(render_id(one))))
