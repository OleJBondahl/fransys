"""Named facts: the one registry the conventions' tables read (spec C5, decision layout-0111).

A fact is a function of one subject, registered by name where it is defined. A boolean fact
answers true or false; a valued fact answers one string of its value set. Every fact carries
a kind tag, and an electrical or physical one names its source in the standards' concept
names. A model fact is a thin wrapper over its derive function, never a copy.
"""

from functools import partial
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

KINDS = ("electrical", "physical", "drawing")
SOURCED_KINDS = ("electrical", "physical")


class Fact(NamedTuple):
    """A registered fact: its name, tag, source, value set (None for boolean) and function."""

    name: str
    kind: str
    source: str
    values: tuple[str, ...] | None
    func: Callable[..., bool | str]


FACTS: dict[str, Fact] = {}


def _register(
    name: str,
    kind: str,
    source: str,
    values: tuple[str, ...] | None,
    func: Callable[..., bool | str],
) -> Callable[..., bool | str]:
    if name in FACTS:
        twice = f"fact {name!r} is registered twice"
        raise ValueError(twice)
    FACTS[name] = Fact(name, kind, source, values, func)
    return func


def fact(
    name: str, *, kind: str = "", source: str = "", values: tuple[str, ...] | None = None
) -> Callable[[Callable[..., bool | str]], Callable[..., bool | str]]:
    """Register the decorated function as the fact `name`; its docstring is the summary."""
    return partial(_register, name, kind, source, values)
