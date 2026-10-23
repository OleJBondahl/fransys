"""The one text order: `natural_key` is refdef's, so `-X2` stands before `-X10` (NUMBER-SORT K7)."""

from typing import Any
lazy from collections.abc import Iterable

import refdef

from .ids import Id, render_id

__all__ = ["NaturalKey", "canonical", "natural_join", "natural_key", "natural_sorted"]

type NaturalKey = tuple[Any, ...]


def natural_key(text: str) -> NaturalKey:
    """Sort key of a printed text: refdef's, so `-W2` sorts before `-W10`.

    Digit runs compare by value, text runs as strings; the whole text is the last tie.
    """
    return refdef.natural_key(text)


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
