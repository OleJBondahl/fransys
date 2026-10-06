"""`mounted_on=`: the mount links of a device that sits on another, from the part facts (EA7)."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._carrier import carrier_function
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import ends_of, pair, poles

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.handles import Port
    from fransys_author.surface._device import Device
    from fransys_author.surface._pairing import PartFacts
    from fransys_author.surface.design import Design


def _label(thing: Device | Fn) -> str:
    return f"{thing._label}.{thing._fn.name}" if isinstance(thing, Fn) else thing._label


def _fns(thing: Device | Fn) -> list[EngineFn]:
    return [thing._fn] if isinstance(thing, Fn) else list(thing._item.functions)


def _poled(facts: PartFacts, fn: EngineFn) -> list[tuple[Port, Port]]:
    """The poles of `fn` that join two pins: a one-port function or a motor has none."""
    found = poles(facts, fn)
    return found if any(a.id != b.id for a, b in found) else []


def _mount_poles(
    design: Design, fn: EngineFn, k: int, carrier: Device | Fn, mounted: Device | Fn
) -> None:
    """Join the one carrier function of `k` poles, load side to line side, pole by pole."""
    facts = design._pairing_facts
    found = carrier_function(
        _fns(carrier),
        lambda c: len(_poled(facts, c)),
        k,
        _label(carrier),
        f"{_label(mounted)}.{fn.name}",
    )
    for a, b in pair(ends_of(facts, found).load, ends_of(facts, fn).line):
        design._engine.link(a, b, kind="mount")


def _mount_marks(design: Design, fn: EngineFn, carrier: Device | Fn, mounted: Device | Fn) -> None:
    """Join each marked pin of the pass-through `fn` to the one carrier pin of equal mark."""
    facts = design._pairing_facts
    for port in fn.ports:
        mark = facts.mark(port)
        if mark is None:
            continue
        hits = [(c, p) for c in _fns(carrier) for p in c.ports if facts.mark(p) == mark]
        where = f"{_label(mounted)}.{fn.name}.{port.name} carries {mark.value}"
        if not hits:
            msg = f"{where}; {_label(carrier)} has no pin of that conductor"
            raise AuthorError(msg)
        if len(hits) > 1:
            names = ", ".join(sorted(f"{c.name}.{p.name}" for c, p in hits))
            msg = f"{where}; {_label(carrier)} has several: {names}"
            raise AuthorError(msg)
        design._engine.link(hits[0][1], port, kind="mount")


def mount(design: Design, mounted: Device | Fn, carrier: Device | Fn) -> None:
    """Write the mount links of `mounted` on `carrier`: poled functions, then pass-throughs."""
    mine = _fns(mounted)
    if {f.id for f in mine} & {f.id for f in _fns(carrier)}:
        msg = f"{_label(mounted)} cannot be mounted on itself"
        raise AuthorError(msg)
    facts = design._pairing_facts
    counts = [(fn, len(_poled(facts, fn))) for fn in mine]
    widest = max((k for _, k in counts), default=0)
    for fn, k in counts:
        if k and k == widest:
            _mount_poles(design, fn, k, carrier, mounted)
        elif not k:
            _mount_marks(design, fn, carrier, mounted)
