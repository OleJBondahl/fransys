"""Source declarations of a supply name, and the pins they put it on (RATINGS-3 R6, ruling Q3 ii).

A name may be declared by a container and again by a unit inside it; only the outermost
declarations are the source. The one reader of that rule.
"""

from typing import TYPE_CHECKING

from .membership import unit_subtree
from .tables import supply_systems

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

    from .core import Port
    from .supply_system import SupplySystem


def _encloses(model: Model, outer: SupplySystem, inner: SupplySystem) -> bool:
    """Whether `outer` sits in a unit strictly above `inner`'s; no unit encloses every unit."""
    if inner.unit is None or outer.unit == inner.unit:
        return False
    return outer.unit is None or inner.unit in unit_subtree(model, outer.unit)


def source_declarations(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """The source declarations of each supply name, in id order.

    A source has no other declaration of its name in a unit strictly above its own; no unit is
    above every unit. Two declarations in one unit, or in sibling units, both count.
    """
    by_name: dict[str, list[SupplySystem]] = {}
    for supply in sorted(supply_systems(model).values(), key=lambda s: s.id):
        by_name.setdefault(supply.name, []).append(supply)
    return {
        name: tuple(d for d in found if not any(_encloses(model, o, d) for o in found))
        for name, found in by_name.items()
    }


def supply_pins(model: Model) -> dict[str, frozenset[Id[Port]]]:
    """The ports a supply name's source declarations put it on, by name."""
    return {
        name: frozenset(pin for supply in sources for pin in supply.pins)
        for name, sources in source_declarations(model).items()
    }
