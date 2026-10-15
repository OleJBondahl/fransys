"""`fn.pole(n)`: one pole of a multi-pole function as a series element (API-FRICTION-2 C5)."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._pairing import NO_SIDE_FIX, Ends, ends_of
from fransys_author.surface._throws import whole_changeover
from fransys_model.vocab import FunctionKind

if TYPE_CHECKING:
    from fransys_author.surface._handles import Fn
    from fransys_author.surface.design import Design


class FnPole:
    """The `n`th pole of a function, counted from 1 in the model's pole order: `s1.main.pole(2)`.

    Does not wire anything: a series wires it as one pole between its neighbours.
    """

    def __init__(self, fn: Fn, n: int) -> None:
        """Hold `fn` and `n`; `Fn.pole` makes these and has checked `n`."""
        self._fn, self._n = fn, n

    def _series_width(self) -> int:
        return 1

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        fn, label = self._fn, f"{self._fn._label}.{self._fn._fn.name}"
        if fn._fn.kind is FunctionKind.CONTACT_CO:
            raise whole_changeover(fn._label, fn._fn)
        ends = ends_of(design._pairing_facts, fn._fn)
        if not ends.line:
            msg = f"{label} has no poles: {NO_SIDE_FIX}"
            raise AuthorError(msg)
        if self._n > len(ends.line):
            count = len(ends.line)
            plural = "" if count == 1 else "s"
            msg = (
                f"{label} has {count} pole{plural}; pole({self._n}) is past the last; "
                f"use a pole from 1 to {count}"
            )
            raise AuthorError(msg)
        i = self._n - 1
        return Ends((ends.line[i],), (ends.load[i],), ends.pe)


def checked(fn: Fn, n: object) -> FnPole:
    """`fn`'s pole `n` as a series element; an `n` that is not an integer from 1 raises."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        where = f"{fn._label}.{fn._fn.name}"
        msg = f"{where}.pole({n!r}) takes a pole number counted from 1: pole(1) is the first"
        raise AuthorError(msg)
    return FnPole(fn, n)
