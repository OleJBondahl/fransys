"""The channels the WAGO export writes under one name (WAGO-CDP, R3658): one reader for `check_plc_names`."""

from typing import TYPE_CHECKING

lazy from fransys_model.derive.cdp_name import cdp_name
lazy from fransys_model.derive.order import plc_racks
lazy from fransys_model.derive.plc_rack_cdp import rack_modules_for_cdp

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.derive.rows_plc import CdpChannel
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function


def _repeats(channels: Iterable[CdpChannel]) -> list[tuple[str, tuple[Id[Function], ...]]]:
    """The names written for more than one of `channels`, each with those channels' functions."""
    names: dict[str, list[Id[Function]]] = {}
    for channel in channels:
        names.setdefault(channel.name, []).append(channel.channel.channel)
    return [(name, tuple(found)) for name, found in names.items() if len(found) > 1]


def cdp_name_repeats(model: Model) -> tuple[tuple[str, tuple[Id[Function], ...]], ...]:
    """Each `(name, channel functions)` written for two or more channels of one module, or of one controller's bound devices.

    The name is `CdpChannel.name`, as `fransys_wago` prints it: the CDP name of the signal, else the channel's label.
    """
    found: list[tuple[str, tuple[Id[Function], ...]]] = []
    for rack in plc_racks(model):
        modules = rack_modules_for_cdp(model, rack)
        found.extend(group for module in modules for group in _repeats(module.channels))
        found.extend(_repeats(c for module in modules for c in module.channels if c.channel.field_device is not None))
    return tuple(dict.fromkeys(found))


def cdp_names_empty(model: Model) -> tuple[tuple[str, Id[Function]], ...]:
    """Each `(signal name, channel function)` of a bound channel whose signal name CDP reads as empty (R3684)."""
    return tuple(
        (name, channel.channel.channel)
        for rack in plc_racks(model)
        for module in rack_modules_for_cdp(model, rack)
        for channel in module.channels
        if channel.channel.field_device is not None and (name := channel.channel.signal_name) and not cdp_name(name)
    )
