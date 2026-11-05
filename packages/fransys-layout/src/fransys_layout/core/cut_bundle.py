"""One bundle's stub per page: its one end stands for every pin of the bundle that continues past the cut (BUNDLE, R1319).

A fan's pins on one page whose undrawn conductors all go to one far page and device are a bundle (CL1 covered rule, R866); a lone-cut fan's
pins on a page are one (R499). Each gets one stub whose end lists the others' pins in `also`, so the plan says which conductors the marker ends.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .values import Ref, RefKind

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from .values import PinRef, RefEnd

__all__ = ("bundled", "leg_stubs")


def bundled(end: RefEnd, rest: Collection[PinRef]) -> RefEnd:
    """`end` as the one end of a bundle: it lists the pins of the `rest` that it stands for."""
    return replace(end, also=tuple(p for p in rest if p != end.pin))


def _is_bundle(ends: Sequence[RefEnd], far: Mapping[PinRef, set[tuple[int, str]]]) -> bool:
    """True when the pins of `ends` (one fan, one page) leave to one far page and the same far devices."""
    sets = [frozenset(far.get(e.pin, ())) for e in ends if e.pin]
    return len(ends) > 1 and len({p for s in sets for p, _ in s}) == 1 and len(set(sets)) == 1


def leg_stubs(ends: Sequence[RefEnd], far: Mapping[PinRef, set[tuple[int, str]]], net_of: Mapping[PinRef, str]) -> list[Ref]:
    """The LEG stubs of one fan's one-sided pins on one page: one for a bundle, else one each."""
    stands = [bundled(ends[0], [e.pin for e in ends if e.pin])] if _is_bundle(ends, far) else list(ends)
    return [Ref(net_of[pin], RefKind.STUB, (e,)) for e in stands if (pin := e.pin) is not None and pin in net_of]
