"""Generic boxes: which side a power pin takes (D5)."""

from dataclasses import replace
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import G_PER_MODULE, generic_box_geometry, symbol_geometry, text_width

if TYPE_CHECKING:
    from .types import DrawnFunction, DrawnPort, Handle


def power_stand(symbol: str, text: str | None) -> int:
    """layout-0132: the width in G of a power `symbol` or its `text`, whichever is wider."""
    return max(symbol_geometry(symbol).body.width, text_width(text or "", height=G_PER_MODULE))


def _forced_sides(ports: tuple[DrawnPort, ...], kind_of: Mapping[Handle, str]) -> dict[str, str]:
    """D5: supply N and ground S for a box with a DC pin; with an AC pin too, AC N, all DC S."""
    dc = {p.symbol_port: kind_of[p.port] for p in ports if p.port in kind_of}
    if not dc:
        return {}
    ac = {p.symbol_port for p in ports if p.ac and p.port not in kind_of}  # V11: AC by current
    sides = {name: _side(kind, has_ac=bool(ac)) for name, kind in dc.items()}
    return {**sides, **dict.fromkeys(ac, "n")}


def _side(kind: str, *, has_ac: bool) -> str:
    """A DC pin's side: N for a supply unless the box has an AC pin, S otherwise."""
    supply = kind == "supply"  # vocab-ok: a `PowerKind` value, which a function kind never is
    return "n" if supply and not has_ac else "s"


def _supply_sides(ports: tuple[DrawnPort, ...], rank_of: Mapping[Handle, int]) -> dict[str, str]:
    """C20: a box on two or more declared potentials has them all on top, else empty."""
    ranked = {p.symbol_port: rank_of[p.port] for p in ports if p.port in rank_of}
    return dict.fromkeys(ranked, "n") if len(set(ranked.values())) >= 2 else {}  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable


def pinned_sides(
    ports: tuple[DrawnPort, ...], rank_of: Mapping[Handle, int], kind_of: Mapping[Handle, str]
) -> dict[str, str]:
    """The ports whose side a box's power decides: D5 when it has a DC pin, else C20."""
    return _forced_sides(ports, kind_of) or _supply_sides(ports, rank_of)


def item_pins(ports: tuple[DrawnPort, ...], sides: Mapping[Handle, str]) -> dict[str, str]:
    """V1: an item box's pins on their function's side, which D5 and C20 do not override."""
    return {p.symbol_port: sides[p.port] for p in ports if p.port in sides}


def power_geometry(
    one: DrawnFunction,
    rank_of: Mapping[Handle, int],
    kind_of: Mapping[Handle, str],
    sides: Mapping[Handle, str],
) -> DrawnFunction:
    """C20, C22, D5 and V1: generic box `one` redrawn with its fixed pins on their sides, ranked."""
    pinned = item_pins(one.ports, sides) or pinned_sides(one.ports, rank_of, kind_of)
    if not pinned:
        return one
    # V1: a pin group is whole, then C22's rank order inside it
    rank = {p.symbol_port: (p.group, rank_of.get(p.port, 0)) for p in one.ports}
    facing = {g.name: g.facing.value for g in one.geometry.ports}
    rest = "" if _forced_sides(one.ports, kind_of) else "s"
    names = [g.name for g in one.geometry.ports]
    names = [
        *sorted((n for n in names if n in pinned), key=lambda n: rank[n]),
        *(n for n in names if n not in pinned),
    ]
    drawn = tuple(pinned.get(n) or rest or facing[n] for n in names)
    geometry = generic_box_geometry(tuple(names), drawn, one.reach, stand=one.stand)
    return replace(one, geometry=geometry)
