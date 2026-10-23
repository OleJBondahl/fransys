"""What a port's MARKING label prints: the part's pin marking, or a power symbol's text."""

from fransys_model.vocab.tables import HasTables, ports
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Port


def port_marking(model: HasTables, port: Id[Port]) -> str:
    """model-0053: what a port's MARKING label prints.

    The part's pin marking (`Port.marking`), else the port's name; "" when the part prints
    none.
    """
    record = ports(model)[port]
    return record.name if record.marking is None else record.marking
