"""Generic boxes: sides and potentials."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from fransys_layout.geometry import GENERIC_BOX_KEY, generic_box_geometry, port_page_at

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
    """C20, V11: each drawn port's potential rank, shipped by the model; unranked ports are out."""
    return {p.port: p.rank for spec in functions for p in spec.ports if p.rank is not None}


def potential_sides(
    drawn: tuple[DrawnFunction, ...],
    rank_of: Mapping[Id[Any], int],
    kind_of: Mapping[Id[Any], str] | None = None,
    sides: Mapping[Id[Any], str] | None = None,
    pairing: tuple[Sequence[BoxFeed], Profile] | None = None,
) -> tuple[DrawnFunction, ...]:
    """C20 (A10), C22: potential ports go N, highest leftmost (24V before 0V), the rest S (D5)."""
    # V1: an item box takes its side in `sides`; layout-0107: `pairing` (feeds, profile) pairs boxes
    kind_of, sides = kind_of or {}, sides or {}
    boxes = tuple(
        power_geometry(one, rank_of, kind_of, sides) if one.geometry.key == GENERIC_BOX_KEY else one
        for one in drawn
    )
    return paired_boxes(boxes, *pairing) if pairing and pairing[0] else boxes


def power_maps(
    power: tuple[PowerEnd, ...], north: tuple[Id[Any], ...], south: tuple[Id[Any], ...]
) -> tuple[dict[Id[Any], str], dict[Id[Any], str]]:
    """D5's power kind and V1's item-box side ("n" or "s"), each by port."""
    kinds = {end.port: end.kind for end in power}
    return kinds, dict.fromkeys(north, "n") | dict.fromkeys(south, "s")


def first_placed(placed: Iterable[PlacedFunction]) -> dict[Id[Any], PlacedFunction]:
    """The first placed function of each function id over `placed`."""
    home: dict[Id[Any], PlacedFunction] = {}
    for one in placed:
        home.setdefault(one.function, one)
    return home


def box_sides(
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
    power: tuple[Mapping[Id[Any], int], Mapping[Id[Any], str], Mapping[Id[Any], str]],
) -> tuple[DrawnFunction, ...]:
    """R7 C5: each generic box drawn with every port on the side facing its placed partners."""
    # `power`: the potential ranks, the power kinds and V1's item-box sides, by port
    drawn_by = {one.function: one for one in drawn}
    where: dict[Id[Any], dict[tuple[int, int], tuple[int, int]]] = {}
    for one in placed:
        geometry = {g.name: g for g in one.geometry.ports}
        for port in drawn_by[one.function].ports:
            g = geometry.get(port.symbol_port)
            if g is not None:
                here = port_page_at(one.at, g)
                where.setdefault(port.port, {})[one.drawing_set, one.page] = (here.x, here.y)
    partners: dict[Id[Any], list[Id[Any]]] = {}
    for c in connections:
        partners.setdefault(c.a.port, []).append(c.b.port)
        partners.setdefault(c.b.port, []).append(c.a.port)
    home = first_placed(placed)
    found = []
    for one in drawn:
        if one.geometry.key != GENERIC_BOX_KEY or one.function not in home or _paired(one):
            found.append(one)
            continue
        found.append(_turned_box(one, home[one.function], where, partners, power))
    return tuple(found)


def _paired(one: DrawnFunction) -> bool:
    """layout-0107: a paired box keeps its resolved pin order and x, `_turned_box` would undo it."""
    return bool(one.fed_by) or one.feeds is not None


def _turned_box(
    one: DrawnFunction,
    box: PlacedFunction,
    where: Mapping[Id[Any], dict[tuple[int, int], tuple[int, int]]],
    partners: Mapping[Id[Any], list[Id[Any]]],
    power: tuple[Mapping[Id[Any], int], Mapping[Id[Any], str], Mapping[Id[Any], str]],
) -> DrawnFunction:
    """R7 C5: one generic box `one`, placed as `box`, drawn with each port on its partners' side."""
    page = (box.drawing_set, box.page)
    centre = box.at.y + one.geometry.body.y + one.geometry.body.height // 2
    symbol_of = {port.symbol_port: port.port for port in one.ports}
    group_of = {port.symbol_port: port.group for port in one.ports}
    rank_of, kind_of, sides = power
    v1 = item_pins(one.ports, sides)
    pinned = v1 or pinned_sides(one.ports, rank_of, kind_of)
    placed_at = []
    for i, g in enumerate(one.geometry.ports):
        side, port = pinned.get(g.name), symbol_of.get(g.name)
        ends = [where[q][page] for q in partners.get(port, ()) if page in where.get(q, {})]
        ranked = rank_of.get(port, 0) if side and (not v1 or port in rank_of) else None
        slot = _slot(side, g.facing.value, ranked, ends, centre)
        placed_at.append((*slot, i, g.name, group_of.get(g.name, 0)))
    # V1, C22: each side's pin groups whole; inside a group the ranked pins first, then the
    # partners' x order; ports with no partner keep theirs
    ordered = sorted(placed_at, key=lambda p: (p[4], p[1] is None, p[1] or 0, p[2]))
    names, drawn = tuple(p[3] for p in ordered), tuple(p[0] for p in ordered)
    geometry = generic_box_geometry(names, drawn, one.reach)
    return one if geometry == one.geometry else replace(one, geometry=geometry)


def _slot(
    side: str | None, facing: str, ranked: int | None, ends: Sequence[tuple[int, int]], centre: int
) -> tuple[str, float | None]:
    """One box port's side (`side`, else partners' turn, else `facing`) and key: rank, x or none."""
    if ranked is not None:
        # C22, D5: a box's power pins keep their side, highest potential leftmost
        return side or facing, -1000 + ranked
    if ends:
        # V1 keeps an item box's pin on its side; C5 turns any other toward its partners
        y = sum(e[1] for e in ends) / len(ends)
        return side or ("n" if y < centre else "s"), sum(e[0] for e in ends) / len(ends)
    # C22: a port with no placed partner keeps its side (C20's supply-on-top rule)
    return side or facing, None
