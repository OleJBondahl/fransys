"""The rack's channel-bearing modules with what a CDP module name and body are made of.

See derive-queries.md.
"""

from fransys_model.vocab.signal_types import SIGNAL_TYPES
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .kinds import cdp_kind
from .plc_rack import plc_rack_modules
from .rows_plc import CdpChannel, CdpRackModule, PlcRackChannel, PlcRackModule


def _direction(channels: tuple[PlcRackChannel, ...], *, output: bool) -> list[CdpChannel]:
    """The configured channels of one direction; `nr` counts every channel of it, a left-out one too."""
    same = [channel for channel in channels if SIGNAL_TYPES[channel.signal].output is output]
    return [CdpChannel(channel=c, cdp_kind=cdp_kind(c.signal), output=output, nr=nr) for nr, c in enumerate(same) if c.configured]


def _module(module: PlcRackModule, ordinal: int) -> CdpRackModule:
    kinds = {cdp_kind(channel.signal) for channel in module.channels}
    channels = (*_direction(module.channels, output=True), *_direction(module.channels, output=False))
    return CdpRackModule(
        module=module,
        ordinal=ordinal,
        description=module.description if module.catalogue_description is None else module.catalogue_description,
        cdp_kind=next(iter(kinds)) if len(kinds) == 1 else None,
        size=len(module.channels),
        channels=tuple(channels),
    )


def rack_modules_for_cdp(model: Model, rack: Id[Item], *, unit: Id[Unit] | None = None) -> tuple[CdpRackModule, ...]:
    """The modules of `rack` that have channels, each with its `ordinal`, `kind` and CDP `channels`.

    A module with no channel (a coupler, an end module) is left out. `ordinal` counts the kept
    modules of one `mpn` in rack order from 0, so an output can letter them. `kind` is the one CDP
    kind (`DI`, `AI`, `DO`, `AO`) all its channels share, `None` when they differ. `channels`:
    outputs first, then inputs, `nr` restarting at 0 in each direction; a channel with
    `configured=False` is left out and its neighbours keep their `nr`. `unit`: as `plc_rack_modules`.

    Raises:
        SchemaError: as `plc_rack_modules` raises it.
    """
    seen: dict[str, int] = {}
    found = []
    for module in plc_rack_modules(model, rack, unit=unit):
        if not module.channels:
            continue
        ordinal = seen.get(module.mpn, 0)
        seen[module.mpn] = ordinal + 1
        found.append(_module(module, ordinal))
    return tuple(found)
