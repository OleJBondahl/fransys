"""Generic boxes: sides and potentials."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from fransys_layout.geometry import generic_box_geometry, port_page_at

from .box_pairing import paired_boxes
from .box_power import item_pins, pinned_sides, power_geometry

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_model.kernel import Id

    from .types import (
        BoxFeed,
        Connection,
        DrawnFunction,
        FunctionSpec,
        PlacedFunction,
        PowerEnd,
        Profile,
    )


def port_ranks(functions: tuple[FunctionSpec, ...]) -> dict[Id[Any], int]:
    """Each drawn port's potential rank, shipped by the model; unranked ports are out."""
    return {p.port: p.rank for spec in functions for p in spec.ports if p.rank is not None}


def potential_sides(
    drawn: tuple[DrawnFunction, ...],
    rank_of: Mapping[Id[Any], int],
    kind_of: Mapping[Id[Any], str] | None = None,
    sides: Mapping[Id[Any], str] | None = None,
    pairing: tuple[Sequence[BoxFeed], Profile] | None = None,
) -> tuple[DrawnFunction, ...]:
    """Potential ports go N, highest leftmost (24V before 0V), the rest S."""
    # An item box takes its side in `sides`; layout-0107: `pairing` (feeds, profile) pairs boxes
    kind_of, sides = kind_of or {}, sides or {}
    boxes = tuple(
        power_geometry(one, rank_of, kind_of, sides) if one.geometry.generic_box else one
        for one in drawn
    )
    return paired_boxes(boxes, *pairing) if pairing and pairing[0] else boxes


def power_maps(
    power: tuple[PowerEnd, ...], north: tuple[Id[Any], ...], south: tuple[Id[Any], ...]
) -> tuple[dict[Id[Any], str], dict[Id[Any], str]]:
    """The power kind and item-box side ("n" or "s"), each by port."""
    kinds = {end.port: end.kind for end in power}
    return kinds, dict.fromkeys(north, "n") | dict.fromkeys(south, "s")


def first_placed(placed: Iterable[PlacedFunction]) -> dict[Id[Any], PlacedFunction]:
    """The first placed function of each function id over `placed`."""
    home: dict[Id[Any], PlacedFunction] = {}
    for one in placed:
        home.setdefault(one.function, one)
    return home


def _port_where(
    placed: tuple[PlacedFunction, ...], drawn_by: Mapping[Id[Any], DrawnFunction]
) -> dict[Id[Any], dict[tuple[int, int], tuple[int, int]]]:
    """Each port's page-space spot, by (drawing set, page)."""
    where: dict[Id[Any], dict[tuple[int, int], tuple[int, int]]] = {}
    for one in placed:
        geometry = {g.name: g for g in one.geometry.ports}
        for port in drawn_by[one.function].ports:
            g = geometry.get(port.symbol_port)
            if g is not None:
                here = port_page_at(one.at, g)
                where.setdefault(port.port, {})[one.drawing_set, one.page] = (here.x, here.y)
    return where


def _partners(connections: tuple[Connection, ...]) -> dict[Id[Any], list[Id[Any]]]:
    """Each port with the ports it connects to."""
    partners: dict[Id[Any], list[Id[Any]]] = {}
    for c in connections:
        partners.setdefault(c.a.port, []).append(c.b.port)
        partners.setdefault(c.b.port, []).append(c.a.port)
    return partners


def box_sides(
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
    power: tuple[Mapping[Id[Any], int], Mapping[Id[Any], str], Mapping[Id[Any], str]],
    aside: frozenset[Id[Any]] = frozenset(),
) -> tuple[DrawnFunction, ...]:
    """Each generic box drawn with every port on the side facing its placed partners.

    A box of a beside column (`aside`, layout-0174) does not face another box: its column reads
    from the host down, and the wire to a box-drawn end is a reference.
    """
    # `power`: the potential ranks, the power kinds and the item-box sides, by port
    where = _port_where(placed, {one.function: one for one in drawn})
    partners = _partners(connections)
    home = first_placed(placed)
    found = []
    for one in drawn:
        if not one.geometry.generic_box or one.function not in home or _paired(one):
            found.append(one)
            continue
        near = _unboxed(partners, drawn) if one.function in aside else partners
        found.append(_turned_box(one, home[one.function], where, near, power))
    return tuple(found)


def turning_ports(
    one: DrawnFunction,
    power: tuple[Mapping[Id[Any], int], Mapping[Id[Any], str], Mapping[Id[Any], str]],
) -> frozenset[Id[Any]]:
    """The ports `box_sides` turns toward their partners: an unpaired generic box's unpinned."""
    rank_of, kind_of, sides = power
    if not one.geometry.generic_box or _paired(one):
        return frozenset()
    pinned = item_pins(one.ports, sides) or pinned_sides(one.ports, rank_of, kind_of)
    return frozenset(p.port for p in one.ports if p.symbol_port not in pinned)


def _unboxed(
    partners: Mapping[Id[Any], list[Id[Any]]], drawn: tuple[DrawnFunction, ...]
) -> dict[Id[Any], list[Id[Any]]]:
    """`partners` less the ports of generic boxes."""
    boxed = {p.port for one in drawn if one.geometry.generic_box for p in one.ports}
    return {port: [q for q in qs if q not in boxed] for port, qs in partners.items()}


def _paired(one: DrawnFunction) -> bool:
    """layout-0107: a paired box keeps its resolved pin order and x, `_turned_box` would undo it.

    A device chain's box keeps them too (layout-0215).
    """
    return bool(one.fed_by) or one.feeds is not None or one.chained


def _turned_box(
    one: DrawnFunction,
    box: PlacedFunction,
    where: Mapping[Id[Any], dict[tuple[int, int], tuple[int, int]]],
    partners: Mapping[Id[Any], list[Id[Any]]],
    power: tuple[Mapping[Id[Any], int], Mapping[Id[Any], str], Mapping[Id[Any], str]],
) -> DrawnFunction:
    """One generic box `one`, placed as `box`, drawn with each port on its partners' side."""
    page = (box.drawing_set, box.page)
    centre = box.at.y + one.geometry.body.y + one.geometry.body.height // 2
    symbol_of = {port.symbol_port: port.port for port in one.ports}
    group_of = {port.symbol_port: port.group for port in one.ports}
    read_order = {port.symbol_port: port.order for port in one.ports}  # the read layer's rank
    rank_of, kind_of, sides = power
    v1 = item_pins(one.ports, sides)
    pinned = v1 or pinned_sides(one.ports, rank_of, kind_of)
    placed_at = []
    for i, g in enumerate(one.geometry.ports):
        side, port = pinned.get(g.name), symbol_of.get(g.name)
        ends = [where[q][page] for q in partners.get(port, ()) if page in where.get(q, {})]
        ranked = rank_of.get(port, 0) if side and (not v1 or port in rank_of) else None
        slot = _slot(side, g.facing.value, ranked, ends, centre)
        placed_at.append((*slot, (read_order.get(g.name, 0), i), g.name, group_of.get(g.name, 0)))
    # Each side's pin groups whole; inside a group the ranked pins first, then marking
    # order (layout-0264): the partners' x never reorders a box's pins
    ordered = sorted(placed_at, key=lambda p: (p[4], p[1] is None, p[1] or 0, p[2]))
    geometry = generic_box_geometry(
        tuple(p[3] for p in ordered), tuple(p[0] for p in ordered), one.reach, stand=one.stand
    )
    return one if geometry == one.geometry else replace(one, geometry=geometry)


def _slot(
    side: str | None, facing: str, ranked: int | None, ends: Sequence[tuple[int, int]], centre: int
) -> tuple[str, int | None]:
    """One box port's side (`side`, else partners' turn, else `facing`) and its rank, if any."""
    if ranked is not None:
        # A box's power pins keep their side, highest potential leftmost
        return side or facing, -1000 + ranked
    if ends:
        # An item box's pin keeps its side; any other turns toward its partners
        y = sum(e[1] for e in ends) / len(ends)
        return side or ("n" if y < centre else "s"), None
    # A port with no placed partner keeps its side (the supply-on-top rule)
    return side or facing, None
