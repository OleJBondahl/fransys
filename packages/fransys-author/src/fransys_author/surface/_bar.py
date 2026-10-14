"""A bar function passed where a pin goes takes its next free screw (PE-BAR B2)."""

from typing import TYPE_CHECKING

from fransys_author._keys import scoped
from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_author.handles import Port
from fransys_author.surface._bar_pe import join_pe
from fransys_author.surface._handles import Fn
from fransys_model.kernel import make_id
from fransys_model.vocab import FunctionKind, PortRole
from fransys_model.vocab import Port as PortRecord

if TYPE_CHECKING:
    from .design import Design


def is_bar(pin: object) -> bool:
    """Whether `pin` is a function of kind `BAR`, not yet a screw."""
    return isinstance(pin, Fn) and pin._fn.kind is FunctionKind.BAR


def _new_screw(fn: Fn, name: str) -> Port:
    """A cut-to-length bar writes no port: each landing makes one, role `PE`."""
    engine = fn._fn
    key = scoped(engine.key, "port", name)
    record = PortRecord(
        id=make_id(PortRecord, key),
        key=key,
        function=engine.id,
        template=None,
        name=name,
        role=PortRole.PE,
    )
    engine._recorder._add(record, caller_origin())
    return Port(id=record.id, key=key, name=name, role=PortRole.PE)


def _taker(design: Design | None, fn: Fn) -> Design:
    """The design that takes a screw of `fn`; a function that is no bar, or no design, raises."""
    if not is_bar(fn):
        msg = f"{fn._label}.{fn._fn.name} is a function, not a pin: name one pin of it"
        raise AuthorError(msg)
    if design is None:
        msg = f"{fn._label}.{fn._fn.name} is a bar: only d.wire or a cable core takes its screw"
        raise AuthorError(msg)
    return design


def take_screw(design: Design | None, fn: Fn) -> Port:
    """The bar's next free screw, joined to the PE net; a full bar raises.

    A function that is no bar is not a pin, and a call with no design takes no screw: both raise.
    """
    design = _taker(design, fn)
    taken = design._screws.get(fn.id, 0)
    if fn.pins:
        if taken == len(fn.pins):
            msg = (
                f"{fn._label}.{fn._fn.name} has {taken} screws and all are taken: "
                "another landing needs a second bar"
            )
            raise AuthorError(msg)
        screw = fn.pins[taken]
    else:
        screw = _new_screw(fn, str(taken + 1))
    design._screws[fn.id] = taken + 1
    join_pe(fn._fn, screw)
    return screw
