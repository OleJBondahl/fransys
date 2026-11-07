"""PLC list, rack and Signals lens row shapes (`derive.plc_tables`, `derive.plc_rack`).

Row shapes beside `rows.py` (model-0199); they import nothing from it.
"""

from decimal import Decimal
from enum import Enum

from fransys_model.kernel import Id, register_enum, value
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import SignalType


@value
class PlcChannelRow:
    """One pin of a PLC channel.

    `pin` is its printed designation (`-A2:5`), `channel_name` the
    channel's own number, `wired_to` the printed far ends at that port joined with `CELL_SEPARATOR`
    (`None` for none). The device fields, `signal_name` and `description` are `None` for an unbound channel.
    """

    channel: Id[Function]
    port: Id[Port]
    pin: str
    channel_name: str
    signal: SignalType
    wired_to: str | None
    field_device: Id[Function] | None
    field_device_designation: str | None
    signal_name: str | None
    description: str | None


@value
class PlcTable:
    """One table of the PLC list: the channels of one controller or module.

    `item` carries the channels, `designation` is its printed designation, the table's heading;
    `rows` are its `PlcChannelRow`s in list order, never empty.
    """

    item: Id[Item]
    designation: str
    rows: tuple[PlcChannelRow, ...]


@value
class ChannelScaling:
    """The `scaling` facet of a field device, projected so a formatter never looks it up."""

    unit: str | None
    raw_min: int
    raw_max: int
    eng_min: Decimal
    eng_max: Decimal


@value
class PlcRackChannel:
    """One channel of a rack module, bound or spare.

    The field fields are `None` for a spare channel, as in `PlcChannelRow`; `scaling` is also
    `None` when the requesting function carries no `scaling` facet. `signal_name` is the bound
    device's request name, else a spare's own name. `routing` and `configured` are its `plc_request`
    settings (`None` and `True` when it has none).
    """

    channel: Id[Function]
    number: int
    signal: SignalType
    field_device: Id[Function] | None
    field_device_designation: str | None
    signal_name: str | None
    routing: str | None
    configured: bool
    scaling: ChannelScaling | None


@value
class PlcRackModule:
    """One PLC module of a rack with its channels, for an output that walks the rack in order.

    `mpn` and `description` are the `Part`'s, projected as `BomLine` does; `catalogue_description` is
    its maker's wording, `None` when it has none. `position` is the item's own `position`, `None`
    when it was never authored.
    """

    module: Id[Item]
    designation: str
    mpn: str
    description: str
    catalogue_description: str | None
    position: int | None
    channels: tuple[PlcRackChannel, ...]


@value
class CdpChannel:
    """One configured channel of a CDP module: `cdp_kind` (DI, AI, DO, AO) and `nr`, its number within its direction."""

    channel: PlcRackChannel
    cdp_kind: str
    output: bool
    nr: int


@value
class CdpRackModule:
    """A channel-bearing rack module with what CDP's module name and body are made of.

    `ordinal` counts the channel-bearing modules of the same `mpn`, in rack order, from 0. `kind` is
    the one CDP kind all its channels share (`cdp_kind`), `None` when they differ; `size` counts all its channels.
    `description` is the part's catalogue wording, else its description. `channels` are the
    configured ones, outputs first, then inputs, each in channel order.
    """

    module: PlcRackModule
    ordinal: int
    description: str
    cdp_kind: str | None
    size: int
    channels: tuple[CdpChannel, ...]


@register_enum
class SignalKind(Enum):
    """The form and direction of a PLC signal."""

    DIGITAL_IN = "digital_in"
    DIGITAL_OUT = "digital_out"
    ANALOGUE_IN = "analogue_in"
    ANALOGUE_OUT = "analogue_out"


@value
class LensChannel:
    """One channel of a PLC module for the Signals lens: its signal kind and field device.

    The device fields are `None` for a spare channel.
    """

    channel: Id[Function]
    number: int
    kind: SignalKind
    signal_name: str | None
    device: Id[Function] | None
    device_item: Id[Item] | None
    device_designation: str | None


@value
class LensModule:
    """One PLC module of the Signals lens with its channels in channel order."""

    module: Id[Item]
    designation: str
    channels: tuple[LensChannel, ...]
