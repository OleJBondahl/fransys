"""What a drawing must show: a row per conductor end at the scope's ports, one per function (0371).

The home of the required-drawn ledger (DRAWN-LEDGER). It lists; `Carried` and the drawn account
(S4b) decide what each row came to.
"""

lazy from collections.abc import Iterable

from fransys_model.derive.carried_functions import accessory_functions
from fransys_model.derive.far_pins import reach
from fransys_model.derive.rows_drawn import FunctionSymbol, Required
from fransys_model.derive.structure import schematic_functions
from fransys_model.kernel import SchemaError
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["required_drawn"]


def required_drawn(model: Model, scope: Iterable[Id[Port]]) -> tuple[Required, ...]:
    """The `ConductorEnd` or `MateEnd` at each `scope` port, then a `FunctionSymbol` per drawn function.

    Ends come in `order.stub_far_order` order (a conductor between two scope ports gives two, a conductor before a mate); the
    functions are `schematic_functions` less an accessory's, in id order. A scope port the model
    does not hold raises `SchemaError`.
    """
    near = tuple(scope)
    held = ports(model)
    for port in near:
        if port not in held:
            msg = f"the scope names a port the model does not hold: {port}; pass its port ids"
            raise SchemaError(msg, kind="port", record_id=port)
    accessory = frozenset(accessory_functions(model))
    return (
        *reach(model, near),
        *(FunctionSymbol(function=f) for f in schematic_functions(model) if f not in accessory),
    )
