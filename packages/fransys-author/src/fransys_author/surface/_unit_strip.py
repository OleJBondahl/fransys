"""A unit's interface strip seen from a container: `d.series` and `d.detail.wire` reach it.

The one place that decides it (decision author-0023); the series and the wire both call it.
"""

from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_model.vocab import Conductor, Function, Item, Port, UnusedBoundary

if TYPE_CHECKING:
    from fransys_author.design import Scope
    from fransys_author.handles import Terminal
    from fransys_author.surface._strip import TerminalStrip
    from fransys_author.surface.design import Design
    from fransys_model.kernel import Id


def is_unit_strip(strip: TerminalStrip | Terminal, design: Design | None) -> bool:
    """True when `strip` (or one of its terminals) was made inside a unit, not `design`'s own."""
    return design is not None and strip._scope is not None and strip._scope is not design._engine


def _unit_name(strip: TerminalStrip) -> str:
    return "/".join(cast("Scope", strip._scope)._prefix)


def _boundary_reading(design: Design) -> tuple[set[Id[Port]], set[Id[Port]], set[Id[Function]]]:
    """Ports wired inside the unit, ports wired outside it, and the functions declared unused."""
    records = design._engine._design._draft.records()
    units = {r.id: r.unit for r in records if isinstance(r, Item)}
    owner = {r.id: units[r.item] for r in records if isinstance(r, Function) and r.item in units}
    unit_of = {r.id: owner.get(r.function) for r in records if isinstance(r, Port)}
    inside: set[Id[Port]] = set()
    outside: set[Id[Port]] = set()
    for c in (r for r in records if isinstance(r, Conductor)):
        for end, other in ((c.a, c.b), (c.b, c.a)):
            held = unit_of[end]
            (inside if unit_of[other] == held else outside).add(end)
    unused = {r.function for r in records if isinstance(r, UnusedBoundary)}
    return inside, outside, unused


def _reach(strip: TerminalStrip, design: Design, count: int) -> tuple[Terminal, ...]:
    """The next `count` boundary terminals of `strip` for a container (author-0040).

    In order, a terminal wired inside and free outside; never one declared unused.
    `_outside` also holds the numbers taken but not yet wired, as in one series call.
    """
    inside, outside, unused = _boundary_reading(design)
    open_ = [
        (n, terminal)
        for n, terminal in sorted(strip._made.items())
        if n not in strip._outside
        and terminal.outer.id not in outside
        and not terminal._fixed
        and terminal.function.id not in unused
    ]
    wired = [n for n, t in open_ if t.inner.id in inside or t.outer.id in inside]
    free = wired + [n for n, _ in open_ if n not in wired]
    if len(free) < count:
        unit = _unit_name(strip)
        msg = (
            f"{strip._tag} of unit {unit} has {len(free)} free boundary terminals, "
            f"{count} needed: a container never adds a terminal to a unit"
        )
        raise AuthorError(msg)
    numbers = free[:count]
    strip._outside.update(numbers)
    return tuple(strip._made[n] for n in numbers)


def take(strip: TerminalStrip, design: Design | None, count: int) -> tuple[Terminal, ...]:
    """The next `count` terminals a series or a wire takes from `strip` as seen from `design`."""
    if design is not None and is_unit_strip(strip, design):
        return _reach(strip, design, count)
    return strip._take(count)


def take_pe(strip: TerminalStrip, design: Design | None) -> Terminal:
    """The PE terminal a PE conductor takes from `strip`: the unit's PE run, else a new one."""
    if not is_unit_strip(strip, design):
        return strip._take_pe()
    run = strip._pe_run
    if run is None:
        unit = _unit_name(strip)
        msg = f"{strip._tag} of unit {unit} has no PE run: the unit makes one with run('PE', n)"
        raise AuthorError(msg)
    return _reach(run, cast("Design", design), 1)[0]
