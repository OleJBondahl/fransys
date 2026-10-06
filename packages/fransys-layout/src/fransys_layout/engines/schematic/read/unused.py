"""V1: the pins and functions with no conductor, and the contacts that are never drawn.

An unwired contact is never drawn (layout-0112): it is a spare, listed in its coil's table. With
`hide_unused_pins`, any other spare function (`derive.function_is_unused`) is left off too, and a
box-drawn function drops its unused ports (`derive.port_is_unused`). IEC symbols keep their fixed
pins, and connector pin views keep their own R7 B5 rule.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read.views import box_drawn
from fransys_layout.stages.resolve import choice_index
from fransys_model.derive import function_is_unused, port_is_unused

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec, SymbolChoice
    from fransys_model.kernel import Model


def without_unused(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    choices: tuple[SymbolChoice, ...],
    *,
    hide: bool,
) -> tuple[tuple[FunctionSpec, ...], tuple[FunctionSpec, ...]]:
    """V1: (the specs still drawn, the spares); an unwired contact is a spare, `hide` or not."""
    table = {(rule.kind, rule.category, rule.gender): rule for rule in DEFAULT_RULES}
    index = choice_index(choices)
    drawn: list[FunctionSpec] = []
    spares: list[FunctionSpec] = []
    for spec in specs:
        unused = spec.pin_function is None and function_is_unused(model, spec.function)
        if unused and (hide or spec.roles.contact):
            spares.append(spec)
        elif hide and spec.pin_function is None and box_drawn(spec, table, index):
            kept = tuple(ref for ref in spec.ports if not port_is_unused(model, ref.port))
            drawn.append(dataclasses.replace(spec, ports=kept))
        else:
            drawn.append(spec)
    return tuple(drawn), tuple(spares)
