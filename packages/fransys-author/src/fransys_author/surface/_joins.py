"""`joins=`: a connector item fitted on its parent device's own leads (HA5, model-0172)."""

from typing import TYPE_CHECKING, cast
lazy from collections.abc import Mapping

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Pin, pick

if TYPE_CHECKING:
    from fransys_author.surface._device import Device
    from fransys_author.surface.design import Design


def _own(port: object, parent: Device) -> Pin:
    """`port` when it is a pin of `parent`; anything else raises."""
    if isinstance(port, Pin) and any(port.id == own.id for _, own in parent._pins()):
        return port
    msg = f"joins= value {port!r} is not a pin of {parent._label}; name a pin such as K1.coil['A1']"
    raise AuthorError(msg)


def _pairs(made: Device, parent: Device, joins: Mapping[str | int, Pin]) -> list[tuple[Pin, Pin]]:
    """The (parent pin, new pin) pairs of `joins`, each pin used once."""
    pairs: list[tuple[Pin, Pin]] = []
    for key, value in joins.items():
        if not isinstance(key, str | int):
            msg = f"joins= key {key!r} must name a pin of {made._label} as a string or an integer"
            raise AuthorError(msg)
        pairs.append((_own(value, parent), pick(made._label, str(key), made._pins())))
    for index in (0, 1):
        names = [pair[index].name for pair in pairs]
        ids = [pair[index].id for pair in pairs]
        if len(set(ids)) != len(ids):
            owner = parent if index == 0 else made
            twice = next(n for n in names if names.count(n) > 1)
            msg = f"joins= uses pin {twice!r} of {owner._label} twice"
            raise AuthorError(msg)
    return pairs


def fit_leads(
    design: Design,
    made: Device,
    parent: object,
    joins: Mapping[str | int, Pin] | None,
) -> None:
    """Write one LEAD link from each joined parent pin to its pin of the new item."""
    if joins is None:
        return
    if not hasattr(parent, "_item"):  # a Device holds its item; a strip, an Fn and None do not
        msg = f"joins= on {made._label} needs parent= a device, got {parent!r}"
        raise AuthorError(msg)
    for port, pin in _pairs(made, cast("Device", parent), joins):
        design._engine.link(port, pin, kind="lead")
