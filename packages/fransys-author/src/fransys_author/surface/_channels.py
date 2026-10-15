"""The PLC channel a series takes for a module passed whole (decision author-0047, C6.5).

A path that ends at the module gives an input, a path that starts at it an output. The kind comes
from the request on a function of the path, else from the module's only kind for that direction.
"""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._ends import Parallel
from fransys_author.surface._handles import Fn
from fransys_model.derive import signal_kind
lazy from fransys_model.vocab import SignalType

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.surface._pairing import PartFacts
    from fransys_model.kernel import Id
    from fransys_model.vocab import Function, PlcRequestFacet

    from .design import Design

_INPUTS = ("digital_in", "analogue_in")
_SHORT = {"di": "DI", "do": "DO", "ai_current": "AI", "ao_current": "AO"}


def _channels(facts: PartFacts, device: Device) -> list[tuple[SignalType, int, EngineFn]]:
    """The channel functions of `device` as (signal, number, function), in channel order."""
    found = []
    for fn in device._item.functions:
        facet = facts.channel(fn)
        if facet is not None:
            found.append((facet.signal, facet.channel, fn))
    return sorted(found, key=lambda c: (c[0].value, c[1], c[2].id))


def _spell(signal: SignalType) -> str:
    return f"fr.{_SHORT[signal.value]}" if signal.value in _SHORT else signal.value


def _requested(
    elements: tuple[object, ...], index: int, asks: dict[Id[Function], PlcRequestFacet]
) -> PlcRequestFacet | None:
    """The request on the function of the path nearest the module, else `None`."""
    near = elements[1:] if index == 0 else reversed(elements[:index])
    return next((asks[e._fn.id] for e in near if isinstance(e, Fn) and e._fn.id in asks), None)


def _kind(
    label: str, way: str, kinds: list[SignalType], asked: PlcRequestFacet | None
) -> SignalType:
    """The signal this path takes: the requested one, else the module's only one this way."""
    if asked is not None and asked.signal not in kinds:
        have = ", ".join(k.value for k in kinds) or "none"
        msg = (
            f"{label} has no {asked.signal.value} {way} for the request "
            f"{asked.signal_name!r}; its {way}s: {have}"
        )
        raise AuthorError(msg)
    if asked is not None:
        return asked.signal
    if len(kinds) == 1:
        return kinds[0]
    if not kinds:
        msg = f"{label} has no PLC {way}, and this path needs one"
        raise AuthorError(msg)
    spoken = " or ".join(f".plc({_spell(k)}, name)" for k in kinds)
    msg = (
        f"{label} has {' and '.join(k.value for k in kinds)} {way}s: "
        f"request one on a function of the path first, {spoken}"
    )
    raise AuthorError(msg)


def _take(design: Design, device: Device, elements: tuple[object, ...], index: int) -> Fn:
    """The lowest free channel of the module at `index`, now taken."""
    if 0 < index < len(elements) - 1:
        msg = (
            f"{device._label} is in the middle of a path: a PLC module ends a path "
            "(an input) or starts one (an output)"
        )
        raise AuthorError(msg)
    facts = design._pairing_facts
    every = _channels(facts, device)
    inward = index != 0
    kinds = sorted(
        {s for s, _, _ in every if (signal_kind(s).value in _INPUTS) == inward},
        key=lambda s: s.value,
    )
    way = "input" if inward else "output"
    signal = _kind(device._label, way, kinds, _requested(elements, index, facts.requests()))
    free = [fn for s, _, fn in every if s is signal and fn.id not in design._taken_channels]
    if not free:
        msg = f"every {signal.value} channel of {device._label} is taken: use another module"
        raise AuthorError(msg)
    design._taken_channels.add(free[0].id)
    return Fn(device._label, free[0], device._scope)


def _fixed(element: object) -> list[Fn]:
    """The functions `element` names, looking inside a `d.parallel`."""
    if isinstance(element, Parallel):
        return [fn for member in element._members for fn in _fixed(member)]
    return [element] if isinstance(element, Fn) else []


def take_channels(design: Design, elements: tuple[object, ...]) -> tuple[object, ...]:
    """`elements` with each whole PLC module replaced by its channel; a fixed channel is taken."""
    facts = design._pairing_facts
    for fn in (fn for element in elements for fn in _fixed(element)):
        if facts.channel(fn._fn) is not None:
            design._taken_channels.add(fn._fn.id)
    return tuple(
        _take(design, e, elements, i) if isinstance(e, Device) and _channels(facts, e) else e
        for i, e in enumerate(elements)
    )
