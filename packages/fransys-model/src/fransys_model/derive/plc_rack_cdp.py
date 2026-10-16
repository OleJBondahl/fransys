"""The rack's channel-bearing modules with the counts a CDP module name is made of.

See derive-queries.md.
"""

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .plc_rack import plc_rack_modules
from .rows_plc import CdpRackModule


def rack_modules_for_cdp(
    model: Model, rack: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[CdpRackModule, ...]:
    """The modules of `rack` that have channels, each with its `ordinal` and `single_signal`.

    A module with no channel (a coupler, an end module) is left out. `ordinal` counts the kept
    modules of one `mpn` in rack order from 0, so an output can letter them; `single_signal` is
    the one signal type all channels share, `None` when they differ. `unit`: as `plc_rack_modules`.

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
        signals = {channel.signal for channel in module.channels}
        single = next(iter(signals)) if len(signals) == 1 else None
        found.append(CdpRackModule(module=module, ordinal=ordinal, single_signal=single))
    return tuple(found)
