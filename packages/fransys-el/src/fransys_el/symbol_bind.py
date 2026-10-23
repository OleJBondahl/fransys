"""The pure half of binding a function's model ports to a symbol's ports (el-0005, el-0014).

A copy of the schematic engine's bind rules (`stages/resolve`): a port's throw, the port map, its
own name, and the pole pair it sits on. Nothing here reads the model.
"""

from typing import TYPE_CHECKING, NamedTuple

from fransys_model.derive.drawing_text import pole_prefix

from .placement_kit import refuse

if TYPE_CHECKING:
    from fransys_layout.symbols import LibrarySymbol
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function

__all__ = ["Part", "Shape", "Target", "member_of", "port_of", "through_ports"]

_THROWS = {"common": "com", "break": "nc", "make": "no"}


class Target(NamedTuple):
    """The symbol's port names, its pole pairs' through ports, and the function's port count."""

    symbol_ports: set[str]
    through: dict[str, str]
    count: int


class Part(NamedTuple):
    """One function bound into a symbol: its shape there and its port map."""

    function: Id[Function]
    shape: Shape
    port_map: frozendict[str, str]


class Shape(NamedTuple):
    """A function's pole count, its pole pairs (first, second port name) and its changeovers."""

    poles: int
    pairs: tuple[tuple[int, str, str], ...]
    thrown: dict[str, tuple[str, int]]


def through_ports(drawn: LibrarySymbol, poles: int) -> tuple[str, str] | None:
    """The base-symbol port names of the symbol's through path; pole 1's ports carry a prefix."""
    first = pole_prefix(0, poles)
    return next(
        (
            (path.from_port.removeprefix(first), path.to_port.removeprefix(first))
            for path in drawn.paths
            if path.through
        ),
        None,
    )


def member_of(shape: Shape, pole: int, poles: int) -> Shape:
    """A one-pole member's shape as pole `pole` of a gang of `poles`."""
    pairs = tuple((pole, first, second) for _, first, second in shape.pairs)
    thrown = {name: (throw, pole) for name, (throw, _) in shape.thrown.items()}
    return Shape(poles, pairs, thrown)


def port_of(name: str, shape: Shape, port_map: frozendict[str, str], at: Target) -> str | None:
    """The symbol port of model port `name`: its throw, the port map, its name, its pole pair."""
    if name in shape.thrown:
        throw, pole = shape.thrown[name]
        if name in port_map:
            refuse(f"port {name}", "a changeover port is bound by its throw, not a port map")
        return pole_prefix(pole, shape.poles) + _THROWS[throw]
    if name in port_map:
        return port_map[name]
    if name in at.symbol_ports:
        return name
    if at.count == 1 and len(at.symbol_ports) == 1:
        return next(iter(at.symbol_ports))
    return at.through.get(name)
