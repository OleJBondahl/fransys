"""The side order of an item box's functions: power above signal, energy in above out, AC above DC.

The key is the one home of the V1 order (layout-0099, 0102; model-0131, 0344). A box puts the
functions that rank first on its north side. The N/S cut stays with the caller.
"""

from fransys_model.derive.facts.energy_flow import gives_energy, takes_energy
from fransys_model.derive.placement_reads import function_ports
from fransys_model.derive.potential import port_potential_current
from fransys_model.vocab.enums import Current
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["side_order_key"]


def side_order_key(model: Model, function: Id[Function]) -> tuple[int, int, int]:
    """The rank of `function` in an item box's side order, lowest first (one 0 or 1 per rule).

    0 where the function is a power function (takes or gives energy), takes energy in, and
    carries AC without DC on its ports; 1 where it does not. The first rule that differs decides.
    """
    currents = {port_potential_current(model, port) for port in function_ports(model, function)}
    takes = takes_energy(model, function)
    ac = Current.AC in currents and Current.DC not in currents
    return (
        0 if takes or gives_energy(model, function) else 1,
        0 if takes else 1,
        0 if ac else 1,
    )
