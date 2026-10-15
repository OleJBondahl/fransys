"""The named facts the overview colours and filters by: an item's kind, a signal's kind.

Reached as `derive.item_kind` and `derive.signal_kind` (model-0197). Both read facts that
already have one home and decide nothing a second time.
"""

lazy from collections.abc import Callable

from fransys_model.vocab.bars import bar_items
from fransys_model.vocab.cables import is_cable
from fransys_model.vocab.enums import FunctionKind, SignalType
from fransys_model.vocab.membership import is_harness, require
from fransys_model.vocab.tables import functions, items
from fransys_model.vocab.terminals import terminal_items
from fransys_model.vocab.unit_index import unit_index
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

from .indexes import build_indexes
from .lookups import strip_set
from .plc_rack import is_plc_module
from .rows import ItemKind
from .rows_plc import SignalKind

__all__ = ["item_kind", "signal_kind"]

_SIGNAL_KINDS = {
    SignalType.DI: SignalKind.DIGITAL_IN,
    SignalType.DO: SignalKind.DIGITAL_OUT,
    SignalType.AI_CURRENT: SignalKind.ANALOGUE_IN,
    SignalType.AI_VOLTAGE: SignalKind.ANALOGUE_IN,
    SignalType.AO_CURRENT: SignalKind.ANALOGUE_OUT,
    SignalType.AO_VOLTAGE: SignalKind.ANALOGUE_OUT,
    SignalType.RTD: SignalKind.ANALOGUE_IN,
    SignalType.RELAY: SignalKind.DIGITAL_OUT,
}


def signal_kind(signal: SignalType) -> SignalKind:
    """The form and direction of a PLC signal type, for a channel's facet or a field request's.

    `DI` is digital in, `DO` and `RELAY` digital out; the two analogue inputs and `RTD` analogue in;
    the two analogue outputs analogue out. A channel and the request it serves give one kind.
    """
    return _SIGNAL_KINDS[signal]


def _only_connectors(model: Model, item: Id[Item]) -> bool:
    """Whether `item` has functions and every one is a `CONNECTOR` (as `box_lines` reads it)."""
    held = build_indexes(model).functions_by_item.get(item, ())
    return bool(held) and all(functions(model)[f].kind is FunctionKind.CONNECTOR for f in held)


# The first test that holds names the kind: a harness wins over its cable, a board over its plugs.
_TESTS: tuple[tuple[ItemKind, Callable[[Model, Item], bool]], ...] = (
    (ItemKind.HARNESS, lambda model, item: is_harness(model, item.id)),
    (ItemKind.CABLE, lambda model, item: is_cable(model, item.id)),
    (ItemKind.TERMINAL, lambda model, item: item.id in terminal_items(model)),
    (ItemKind.STRIP, lambda model, item: item.id in strip_set(model)),
    (ItemKind.PLC_MODULE, is_plc_module),
    (ItemKind.BOARD, lambda model, item: item.part in unit_index(model).pcb_parts),
    (ItemKind.BAR, lambda model, item: item.id in bar_items(model)),
    (ItemKind.CONNECTOR, lambda model, item: _only_connectors(model, item.id)),
)


def item_kind(model: Model, item: Id[Item]) -> ItemKind:
    """What `item` is: harness, cable, terminal, strip, PLC module, board, bar, connector or device.

    The first that holds, in that order. Each test is the one predicate that already decides it:
    `is_harness`, `is_cable`, `terminal_items`, `strip_set`, `is_plc_module`, a part with a `pcb`
    facet, `bar_items`, and an item whose functions are all connectors. `DEVICE` is the rest.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    record = require(items(model).get(item), "item", item)
    return next((kind for kind, test in _TESTS if test(model, record)), ItemKind.DEVICE)
