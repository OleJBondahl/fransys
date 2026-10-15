"""A device with no part ends a series: its pins are the last element's poles, in declared order."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import PartFacts, ends_of, label_of, poles

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.surface._pairing import Ends

_FIX = "make it the last element, or wire it per core with d.detail.wire(pin, pin, wire=...)"
_EARTH = "declare the earth pin apart and wire it with d.earth"


def _fns(element: object) -> list[EngineFn]:
    if isinstance(element, Device):
        return list(element._item.functions)
    return [element._fn] if isinstance(element, Fn) else []


def partless(facts: PartFacts, element: object) -> bool:
    """Whether `element`, or a member of it, is a function or device made without a part."""
    members = getattr(element, "_members", None)
    if members is not None:
        return any(partless(facts, member) for member in members)
    return any(facts.partless(fn) for fn in _fns(element))


def only_last(facts: PartFacts, elements: tuple[object, ...]) -> None:
    """Raise `AuthorError` for a part-less element anywhere but the end of the series."""
    last = len(elements) - 1
    for i, element in enumerate(elements):
        if not partless(facts, element):
            continue
        label = label_of(element)
        if hasattr(element, "_members"):
            msg = f"{label} holds a device with no part, which cannot sit in a group: {_FIX}"
            raise AuthorError(msg)
        if i != last:
            msg = f"{label} has no part and sits at position {i + 1} of {last + 1}: {_FIX}"
            raise AuthorError(msg)


def box_ends(facts: PartFacts, label: str, fns: list[EngineFn], width: int | None) -> Ends:
    """The ends of the one function of a part-less device, whose pin count must equal `width`."""
    if len(fns) != 1:
        msg = f"{label} has no part and {len(fns)} functions: {_FIX}"
        raise AuthorError(msg)
    count = len(poles(facts, fns[0], partless_ok=True))
    if width is not None and count != width:
        msg = (
            f"{label} has {count} non-earth pin{'' if count == 1 else 's'} where the path "
            f"carries {width} pole{'' if width == 1 else 's'}: {_EARTH}"
        )
        raise AuthorError(msg)
    return ends_of(facts, fns[0], partless_ok=True)
