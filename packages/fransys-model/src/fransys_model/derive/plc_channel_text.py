"""The one printed text of a PLC channel: the pins the PLC list prints for it (`-A2:5, -A2:6`)."""

from fransys_model.derive.designation import port_designation
from fransys_model.derive.facts.roles import plc_channel_facets
from fransys_model.derive.indexes import Indexes, build_indexes
from fransys_model.derive.order import natural_key
from fransys_model.vocab.tables import functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port, Unit

__all__ = ["channel_pin_designations", "plc_channel_text"]


def channel_pin_designations(
    model: Model, idx: Indexes, function: Id[Function], unit: Id[Unit] | None = None
) -> tuple[tuple[Id[Port], str], ...]:
    """Each pin of `function` with its printed designation, in the PLC list's pin order."""
    pins = sorted(
        idx.ports_by_function.get(function, ()), key=lambda p: natural_key(ports(model)[p].name)
    )
    return tuple((port, port_designation(model, port, unit=unit)) for port in pins)


def plc_channel_text(model: Model, function: Id[Function]) -> str | None:
    """Channel `function`'s pins in list order, joined by ", "; `None` if it is no PLC channel."""
    if functions(model)[function].template not in plc_channel_facets(model):
        return None
    pins = channel_pin_designations(model, build_indexes(model), function)
    return ", ".join(text for _, text in pins) or None
