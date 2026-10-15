"""The pins and functions with no conductor, and the contacts that are never drawn.

An unwired contact is never drawn (layout-0112): it is a spare, listed in its coil's table. With
`hide_unused_pins`, any other spare function (`derive.function_is_unused`) is left off too, and a
box-drawn function drops its unused ports (`derive.port_is_unused`), but a boundary box whose
every port is spare keeps them (layout-0139). IEC symbols keep their fixed
pins, and connector pin views keep their own rule. A unit's boundary function is never
a spare (layout-0139): its replica column needs its spec.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read.units import boundary_edge_set
from fransys_layout.engines.schematic.read.views import box_drawn
from fransys_layout.stages.resolve import choice_index
from fransys_model.derive import function_is_unused, port_is_unused

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec, PortSpec, SymbolChoice
    from fransys_model.kernel import Model


def without_unused(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    choices: tuple[SymbolChoice, ...],
    *,
    hide: bool,
) -> tuple[tuple[FunctionSpec, ...], tuple[FunctionSpec, ...]]:
    """(the specs still drawn, the spares); an unwired contact is a spare, `hide` or not."""
    table = {(rule.kind, rule.category, rule.gender): rule for rule in DEFAULT_RULES}
    index = choice_index(choices)
    boundaries = boundary_edge_set(model)
    drawn: list[FunctionSpec] = []
    spares: list[FunctionSpec] = []
    for spec in specs:
        unused = (
            spec.pin_function is None
            and spec.function not in boundaries
            and all(function_is_unused(model, member) for member in spec.members)
        )
        if unused and (hide or spec.roles.contact):
            spares.append(spec)
        elif hide and spec.pin_function is None and box_drawn(spec, table, index):
            kept = tuple(ref for ref in spec.ports if not port_is_unused(model, ref.port))
            # A boundary box with every port spare keeps them: no port, nothing to place
            drawn.append(_cut(spec, kept) if kept else spec)
        else:
            drawn.append(spec)
    return tuple(drawn), tuple(spares)


def _cut(spec: FunctionSpec, kept: tuple[PortSpec, ...]) -> FunctionSpec:
    """`spec` with `kept` ports, and only the pole pairs whose two ports it keeps (layout-0236)."""
    names = {ref.name for ref in kept}
    pairs = tuple(p for p in spec.pole_pairs if {p.first, p.second} <= names)
    return dataclasses.replace(spec, ports=kept, pole_pairs=pairs)
