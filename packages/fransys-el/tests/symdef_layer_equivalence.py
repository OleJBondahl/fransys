"""The symdef layer against the old builder (layout-0316 D): every value, every orientation.

`diffs` lists where a layer-built `Sym` departs from the old builder's flat R0 values (kept in
`oracle_syms.py`) and from those values turned by symdef's `orient` at each other view.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from conventions_fixtures import house
from fransys_el.placement_env import make_env
from fransys_el.placement_syms import syms_of
from oracle_syms import Old, old_of
from placement_fixtures import leads
from turns_by_path import turn_fixtures

from electrical_symbols import LIBRARY

if TYPE_CHECKING:
    from fransys_el.placement_kit import SymbolKit

    from fransys_layout.core import Box, Sym
    from fransys_model.kernel import Model

__all__ = ["checked", "diffs", "pairs"]


def tables(model: Model, kit: SymbolKit) -> dict[str, Box]:
    """The contact-table box of each coil of `kit` that has one, by symbol id."""
    found: dict[str, Box] = {}
    syms_of(make_env(model, kit, house(), LIBRARY), found)
    return found


def pairs(model: Model, kit: SymbolKit) -> list[tuple[Old, Sym]]:
    """The old builder's values and the layer-built `Sym` of each function of `kit`."""
    env = make_env(model, kit, house(), LIBRARY)
    built = {s.id: s for s in syms_of(env)}
    return [
        (old_of(env, lead, pick), built[env.ids[lead]]) for lead, pick in leads(env.kit).items()
    ]


def diffs(old: Old, new: Sym) -> list[str]:
    """One line per value of `new` that is not the old value (R0) or its turn (other views).

    A coil's table is an Anchor now (R327): only its height is compared, and the footprint is not.
    """
    turns = turn_fixtures()
    found = []
    flat = {
        "label": (old.label, new.label),
        "pins": (old.pins, new.pins),
        "nodes": (old.nodes, new.nodes),
        "box": (old.box, new.box),
        "orientations": (old.orientations, frozenset(new.views)),
    }
    found += [f"{k}: {a} != {b}" for k, (a, b) in flat.items() if a != b]
    for orient, view in new.views.items():
        want = {
            "body": turns.turn_box(old.body, orient),
            "keepout": turns.turn_box(old.keepout, orient),
            "footprint": turns.turn_box(old.footprint, orient),
            "row_footprint": None
            if old.row_footprint is None
            else turns.turn_box(old.row_footprint, orient),
            "pins": tuple(turns.turn_pin(p, orient) for p in old.pins),
        }
        found += [
            f"{orient} {k}: {v} != {getattr(view, k)}"
            for k, v in want.items()
            if v != getattr(view, k) and not (k == "footprint" and old.table is not None)
        ]
    return found


def checked(model: Model, kit: SymbolKit) -> list[str]:
    """Every difference over `kit`, each prefixed with the symbol's id."""
    return [f"{new.id} {line}" for old, new in pairs(model, kit) for line in diffs(old, new)]


def planted(new: Sym) -> Sym:
    """`new` with its R180 footprint one grid division wider: the difference `diffs` must see."""
    view = new.views["R180"]
    wider = replace(view.footprint, w=view.footprint.w + 1)
    return replace(new, views={**new.views, "R180": replace(view, footprint=wider)})
