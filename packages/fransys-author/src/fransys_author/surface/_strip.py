"""Terminal strips: `d.terminal_strip("X1", part)` and `X1[3]`, terminal 3 by number (EA9)."""

from typing import TYPE_CHECKING
lazy from collections.abc import Callable
lazy from types import EllipsisType

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device, _mark_boundary, _one_maker, part_mpn
from fransys_author.surface._runs import check_run
from fransys_author.surface._tags import floating_name
from fransys_author.surface._unit_strip import take
lazy from fransys_author._origin import caller_origin
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Group, Strip, Terminal, _write_placement
lazy from fransys_author.surface._pairing import End, Ends

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


PE_LABEL = "PE"  # IEC 60445: the protective conductor's name; a run so labelled is PE terminals


def _need_pe(strip: TerminalStrip) -> None:
    """Raise `AuthorError` when `strip` has no `pe=` part (a feed-through part is never PE)."""
    if strip._pe_mpn is None:
        msg = f"{strip._tag} has no PE terminal part: terminal_strip(..., pe=P.X)"
        raise AuthorError(msg)


class TerminalStrip:
    """One strip: `X1[3]` is its terminal 3, made on first use and the same handle after.

    A terminal joins the function block it is first taken in, else the strip's own group.
    Does not pick a terminal for `X1[3]`: a number is explicit; `take` picks the next free ones.
    """

    def __init__(  # noqa: PLR0913 -- the strip's facts and the engine's bridge, keyword-only
        self,
        tag: str,
        strip: Strip,
        mpn: str,
        count: int | None,
        pe_mpn: str | None = None,
        *,
        bridge: Callable[..., None] | None = None,
        group: Callable[[], Group | None] = lambda: None,
        boundary: Callable[[Terminal], None] | None = None,
        scope: Scope | None = None,
    ) -> None:
        """Wrap the engine `strip` of `tag`; `group` reads the open block, `boundary` marks."""
        self._tag, self._strip, self._mpn, self._count = tag, strip, mpn, count
        self._pe_mpn, self._bridge = pe_mpn, bridge
        self._now, self._boundary, self._scope = group, boundary, scope
        self._runs: set[str] = set()
        self._outside: set[int] = set()  # numbers a container took through `d.series` or `d.wire`
        self._pe_run: Run | None = None
        self._made: dict[int, Terminal] = {}
        self._used: set[int] = set()
        self._placed: set[int] = set()
        for number in range(1, (count or 0) + 1):
            self._terminal(number)

    _grows = False  # a run with no size: its terminals come in order, each bridged to the last
    _group = ""  # the engine group text its terminals count up in; a run sets its label

    def _terminal(self, number: int, mpn: str | None = None) -> Terminal:
        """Terminal `number`, made on first use with `mpn` (the strip's part by default)."""
        if number not in self._made:
            made = self._strip.terminal(mpn or self._mpn, self._group, index=number)
            object.__setattr__(made, "_scope", self._scope)  # frozen, init=False field
            if self._boundary is not None:
                self._boundary(made)
            self._made[number] = made
            if self._grows and number > 1 and self._bridge is not None:
                self._bridge(self._made[number - 1], made)
        return self._made[number]

    def _claim(self, *numbers: int) -> None:
        """Place each terminal not yet placed at the open function block, if there is one."""
        group = self._now()
        for number in numbers:
            if number not in self._placed:
                self._placed.add(number)
                if group is not None:
                    terminal = self._made[number]
                    _write_placement(
                        self._strip._recorder, terminal.id, terminal.key, group, caller_origin()
                    )

    def __getitem__(self, number: int) -> Terminal:
        """Terminal `number`, counted from 1.

        Does not accept a number past `count`, or a text: it raises.
        """
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            msg = f"{self._tag}[{number!r}]: a terminal number is an integer from 1"
            raise AuthorError(msg)
        if self._count is not None and number > self._count:
            msg = f"{self._tag} has {self._count} terminals; {number} is past the last"
            raise AuthorError(msg)
        if self._grows and number not in self._made:
            msg = f"{self._tag} has {len(self._made)} so far; give the run a size for {number}"
            raise AuthorError(msg)
        self._used.add(number)
        terminal = self._terminal(number)
        self._claim(number)
        return terminal

    def _free(self, count: int) -> list[int]:
        """The `count` lowest numbers not used; raise when `count` strip terminals run out."""
        numbers: list[int] = []
        number = 0
        while len(numbers) < count:
            number += 1
            if number not in self._used:
                numbers.append(number)
        if self._count is not None and numbers and numbers[-1] > self._count:
            msg = f"{self._tag} has {self._count} terminals; the series needs {numbers[-1]}"
            raise AuthorError(msg)
        return numbers

    def _take(self, count: int) -> tuple[Terminal, ...]:
        """The next `count` free terminals, the lowest numbers not named; marks them used."""
        numbers = self._free(count)
        self._used.update(numbers)
        taken = tuple(self._terminal(number) for number in numbers)
        self._claim(*numbers)
        return taken

    def _take_pe(self) -> Terminal:
        """One PE terminal of the `pe=` part, the next free number; raises without `pe=`."""
        _need_pe(self)
        (number,) = self._free(1)
        self._used.add(number)
        terminal = self._terminal(number, self._pe_mpn)
        self._claim(number)
        return terminal

    def run(
        self, label: str, count: int | None = None, *, bridged: bool | tuple[int, int] = False
    ) -> Run:
        """A named run of `count` terminals that counts inside `label`, bridged when asked.

        `bridged=True` jumpers the whole run; `bridged=(first, last)` terminals `first` to `last`.
        With no `count` the run is `bridged=True` and grows, each new terminal bridged to the last.
        Does not shift, or get shifted by, the strip's own numbering or another run.
        A run labelled exactly "PE" takes the strip's `pe=` part and raises without one.
        """
        if label == PE_LABEL:
            _need_pe(self)
        check_run(self, label, count, bridged)
        run = Run(self, label, count, bridged=bridged)
        if label == PE_LABEL:
            self._pe_run = run
        return run

    _enters_from_field = True  # a series that comes from a cable enters at the outer side

    def _series_width(self) -> None:
        """A strip has no width of its own: the series gives it one."""

    def _series_ends(self, design: Design, width: int | None) -> Ends:
        """The line ends (inner) and load ends (outer) of `width` taken terminals."""
        terminals = take(self, design, width or 1)
        return Ends(
            line=tuple(End(t.inner, None) for t in terminals),
            load=tuple(End(t.outer, None) for t in terminals),
        )


class Run(TerminalStrip):
    """`count` terminals of a strip that count up inside their own label, from 1.

    Does not share numbering with the strip or another run; a series may name it as a strip.
    """

    def __init__(
        self,
        strip: TerminalStrip,
        label: str,
        count: int | None,
        *,
        bridged: bool | tuple[int, int],
    ) -> None:
        """Declare the run `label` on `strip`; `X3.run` makes these."""
        self._group = label
        self._grows = count is None
        tag = f"{strip._tag}.run({label!r})"
        super().__init__(
            tag,
            strip._strip,
            strip._pe_mpn if label == PE_LABEL and strip._pe_mpn else strip._mpn,
            count,
            strip._pe_mpn,
            bridge=strip._bridge,
            group=strip._now,
            boundary=strip._boundary,
            scope=strip._scope,
        )
        if bridged and count is not None and strip._bridge is not None:
            first, last = (1, count) if bridged is True else bridged
            numbers = range(first, last + 1)
            strip._bridge(*(self._terminal(number) for number in numbers))
            self._claim(*numbers)


def _boundary_marker(
    design: Design, *, interface: bool, unused: bool
) -> Callable[[Terminal], None] | None:
    """The call that marks a terminal a boundary as `device` does, or `None` when neither is set."""
    if not (interface or unused):
        return None
    return lambda terminal: _mark_boundary(
        design,
        terminal,
        interface=interface,
        unused=unused,
    )


class Strips:
    """The `terminal_strip` call of `Design`."""

    def terminal_strip(  # noqa: PLR0913 -- one keyword per strip fact, as `device` has
        self: "Design",
        tag: str | None,
        part: str | type[Device],
        count: int | None = None,
        *,
        name: str | None = None,
        description: str = "",
        place: str | EllipsisType | None = ...,
        pe: str | type[Device] | None = None,
        interface: bool = False,
        unused: bool = False,
        external: bool = False,
    ) -> TerminalStrip:
        """Add terminal strip `tag` (printed `-tag`) of terminal `part`, `count` terminals if given.

        Does not take a prefixed tag. `tag=None` needs `name=`; `external=True` flags its terminals.
        """
        mpn = part_mpn(part)
        pe_mpn = None if pe is None else part_mpn(pe)
        _one_maker(self, mpn)
        if pe_mpn is not None:
            _one_maker(self, pe_mpn)
        name = floating_name(tag, name, "terminal_strip")
        where = self._place if place is ... else place
        self._claim(name or tag or "", per_function=False)
        strip = self._engine.strip(
            tag, name=name, at=self._place_node(where), description=description, external=external
        )
        return TerminalStrip(
            name or tag or "",
            strip,
            mpn,
            count,
            pe_mpn,
            bridge=self._engine.bridge,
            group=lambda: self._group,
            boundary=_boundary_marker(self, interface=interface, unused=unused),
            scope=self._engine,
        )
