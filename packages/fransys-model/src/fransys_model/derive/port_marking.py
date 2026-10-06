"""What a port's MARKING label prints: the part's pin marking, or a power symbol's text (D5)."""

from fransys_model.derive.power import port_power_text
from fransys_model.layout import POWER_SLOT
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Port


def port_marking(model: Model, port: Id[Port]) -> str:
    """model-0053 (F2): what a port's MARKING label prints.

    The part's pin marking (`Port.marking`), else the port's name; "" when the part prints
    none.
    """
    record = ports(model)[port]
    return record.name if record.marking is None else record.marking


def marking_text(model: Model, port: Id[Port], slot: str) -> str:
    """A MARKING label's text: the net's text in the power slot, else the port's marking."""
    if slot == POWER_SLOT:
        return port_power_text(model, port) or ""
    return port_marking(model, port)
