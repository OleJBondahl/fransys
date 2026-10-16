"""Fixed terminals in a series: `x1[3]`, `x1[1:4]` and `(x1[3], x2[3])` (API-CLARITY C6.11)."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.handles import Port, Terminal
from fransys_author.surface._pairing import End, Ends

if TYPE_CHECKING:
    from fransys_author.surface._strip import TerminalStrip
    from fransys_author.surface.design import Design

_MARK = "terminal"


def take(design: Design, terminal: Terminal) -> None:
    """Mark a terminal a container named by number: a whole-strip take skips it."""
    if terminal._scope is not None and terminal._scope is not design._engine:
        object.__setattr__(terminal, "_fixed", True)  # frozen, init=False field


def side_ends(design: Design, port: Port) -> Ends | None:
    """The ends of a series element that is one terminal's `.inner` or `.outer`, else `None`.

    The side is pinned: the port stands as both the line and the load end.
    """
    if port._terminal is None:
        return None
    take(design, port._terminal)
    end = (End(port, None),)
    return Ends(line=end, load=end)


class FixedTerminals:
    """Terminals named by number as one series element, one terminal per pole, in order.

    Behaves as a strip passed whole does (inner side in, outer side out), with these numbers.
    """

    _enters_from_field = True  # a series that comes from a cable enters at the outer side

    def __init__(self, terminals: tuple[Terminal, ...], label: str) -> None:
        """Hold `terminals`; `x1[a:b]` and a series' tuple make these."""
        self._terminals, self._label = terminals, label

    @property
    def outer(self) -> tuple[Port, ...]:
        """The field-side port of each terminal, in order: a series element pinned to that side.

        Does not change the terminals taken: it is the slice's `.outer`, as one terminal has.
        """
        return tuple(t.outer for t in self._terminals)

    @property
    def inner(self) -> tuple[Port, ...]:
        """The internal-side port of each terminal, in order: a series element pinned to that side.

        Does not change the terminals taken: it is the slice's `.inner`, as one terminal has.
        """
        return tuple(t.inner for t in self._terminals)

    def _series_width(self) -> int | None:
        """One terminal takes the series' width; several set it."""
        return len(self._terminals) if len(self._terminals) > 1 else None

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the protocol
        for t in self._terminals:
            take(design, t)
        return Ends(
            line=tuple(End(t.inner, None) for t in self._terminals),
            load=tuple(End(t.outer, None) for t in self._terminals),
        )


def _form_refusal(tag: str, picked: slice) -> str | None:
    """Why `picked` is not `a:b` with both ends, `None` when it is."""
    if picked.step is not None:
        first, end = picked.start or 1, picked.stop or 4
        return f"{tag}[a:b] takes no step: write {tag}[{first}:{end}], terminals in order"
    if not isinstance(picked.start, int) or not isinstance(picked.stop, int):
        return f"{tag}[a:b] names both ends: {tag}[1:4] is terminals 1, 2 and 3"
    return None


def _bounds_refusal(strip: TerminalStrip, first: int, end: int) -> str | None:
    """Why terminals `first` up to `end` cannot be taken from `strip`, `None` when they can."""
    tag = strip._tag
    if end <= first:
        return f"{tag}[{first}:{end}] holds no terminal: the end is excluded, {tag}[1:4] is 1 to 3"
    if first < 1:
        return f"{tag}[{first}:{end}] starts below terminal 1: write {tag}[1:{end - first + 1}]"
    if strip._count is not None and end - 1 > strip._count:
        return f"{tag} has {strip._count} terminals; {tag}[{first}:{end}] reaches past the last"
    return None


def numbers(strip: TerminalStrip, picked: slice) -> range:
    """The terminal numbers `picked` takes from `strip`; raises the slice's refusal."""
    why = _form_refusal(strip._tag, picked)
    if why is None:
        why = _bounds_refusal(strip, picked.start, picked.stop)
    if why is not None:
        raise AuthorError(why)
    return range(picked.start, picked.stop)


def span(strip: TerminalStrip, picked: slice) -> FixedTerminals:
    """`strip[a:b]`: terminals `a` up to but not including `b`; each one counts as taken."""
    taken = numbers(strip, picked)
    terminals = tuple(strip[number] for number in taken)
    return FixedTerminals(terminals, f"{strip._tag}[{taken.start}:{taken.stop}]")


def _where(terminal: Terminal) -> tuple[tuple[str, ...], int] | None:
    """The strip key and number of a terminal made without a run label, else `None`."""
    key = terminal.key
    if len(key) < 2 or key[-2] != _MARK or not key[-1].isdigit():  # noqa: PLR2004 -- a mark and a number
        return None
    return key[:-2], int(key[-1])


def _in_order(terminals: tuple[Terminal, ...]) -> str | None:
    """`strip[a:b]` when `terminals` run in order on one strip, else `None`."""
    places = [place for place in map(_where, terminals) if place is not None]
    if len(places) != len(terminals) or len({strip for strip, _ in places}) != 1:
        return None
    numbers = [number for _, number in places]
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        return None
    return f"{places[0][0][-1].lower()}[{numbers[0]}:{numbers[-1] + 1}]"


def _refuse_repeat(held: tuple[Terminal, ...]) -> None:
    """Raise when one terminal stands twice in a tuple: it would take two poles."""
    ids = [t.id for t in held]
    if twice := next((t for t in held if ids.count(t.id) > 1), None):
        name = ":".join(part for part in twice.key if part != _MARK)
        msg = f"a tuple in a series names terminal {name} twice: one terminal is one pole"
        raise AuthorError(msg)


def fixed(element: Terminal | tuple[object, ...]) -> FixedTerminals:
    """A terminal or a tuple of terminals as a series element; a tuple in order raises."""
    items = (element,) if isinstance(element, Terminal) else element
    held = tuple(t for t in items if isinstance(t, Terminal))
    if len(held) != len(items):
        other = next(t for t in items if not isinstance(t, Terminal))
        kind = "a mix of pins and terminals" if isinstance(other, Port) else type(other).__name__
        msg = (
            "a tuple in a series holds fixed terminals (x1[3], x2[3]) or the pins of one device "
            f"(k1.coil.A1, k1.coil.A2), not {kind}"
        )
        raise AuthorError(msg)
    _refuse_repeat(held)
    if len(held) > 1 and (written := _in_order(held)) is not None:
        msg = f"these terminals run in order on one strip: write {written}"
        raise AuthorError(msg)
    return FixedTerminals(held, "fixed terminals")


def fixed_count(element: object) -> int | None:
    """The terminals a fixed element names (a pinned side is one), `None` for any other element.

    A series of fixed terminals alone takes its width from the first of these.
    """
    if isinstance(element, Port):
        return None if element._terminal is None else 1
    if isinstance(element, tuple):
        return len(element)
    if isinstance(element, Terminal):
        return 1
    return len(element._terminals) if isinstance(element, FixedTerminals) else None
