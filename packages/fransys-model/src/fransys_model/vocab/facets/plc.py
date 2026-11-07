"""Facets: PLC channel declaration, field request and allocation (facets.md and examples.md)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.templates import FunctionTemplate


@record(kind="facet.plc_channel", subject="subject", unique=True)
class PlcChannelFacet:
    """Which signal type and channel number a module's `FunctionTemplate` provides.

    Example: a PLC module's channel-3 template carries `signal=SignalType.DI,
    channel=3`. Read by `passes.plc_allocation` and `validators.plc`
    (`PLC_BINDING_SIGNAL_MISMATCH`, `PLC_BINDING_WIRING_MISMATCH`).
    """

    id: Id[PlcChannelFacet]
    key: AuthoringKey
    subject: Id[FunctionTemplate]
    signal: SignalType
    channel: int
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.plc_request", subject="subject", unique=True)
class PlcRequestFacet:
    """A channel's PLC settings: a field function's request for a channel, or a spare channel's own.

    Example: the design/examples.md 11 transmitter's `Function` carries
    `signal=SignalType.AI_CURRENT, signal_name="Pos", priority=1`. Served by
    `passes.plc_allocation` in `(priority, function key)` order. A channel function with
    `signal=None` is a spare and these are its settings (WAGO-CDP, designer R1824); `routing` is an
    opaque CDP path, `None` writes none; `configured=False` leaves the channel out of the CDP file.
    """

    id: Id[PlcRequestFacet]
    key: AuthoringKey
    subject: Id[Function]
    signal: SignalType | None
    signal_name: str | None
    priority: int
    routing: str | None = None
    configured: bool = True
    ext: frozendict[str, Value] = frozendict()


@record(kind="facet.plc_binding", subject="subject", unique=True)
class PlcBindingFacet:
    """The channel a `plc_request` was allocated to; written only by the allocation pass.

    Example: the design/examples.md 11 transmitter's request binds to a DI module's
    channel-3 `Function`. Guarded by `validators.plc` (`PLC_BINDING_SIGNAL_MISMATCH`: the bound
    channel's signal must match the request's; `PLC_BINDING_WIRING_MISMATCH`: what is wired
    to the request and the channel must agree with the binding).
    """

    id: Id[PlcBindingFacet]
    key: AuthoringKey
    subject: Id[Function]
    channel: Id[Function]
    ext: frozendict[str, Value] = frozendict()
