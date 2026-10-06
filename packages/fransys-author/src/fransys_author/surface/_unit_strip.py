"""A unit's interface strip seen from a container: `d.series` and `d.wire` reach its terminals.

The one place that decides it (decision author-0023); the series and the wire both call it.
"""

from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_model.vocab import Conductor

if TYPE_CHECKING:
    from fransys_author.design import Scope
    from fransys_author.handles import Terminal
    from fransys_author.surface._strip import TerminalStrip
    from fransys_author.surface.design import Design


def is_unit_strip(strip: TerminalStrip | Terminal, design: Design | None) -> bool:
    """True when `strip` (or one of its terminals) was made inside a unit, not `design`'s own."""
    return design is not None and strip._scope is not None and strip._scope is not design._engine


def _unit_name(strip: TerminalStrip) -> str:
    return "/".join(cast("Scope", strip._scope)._prefix)


def _reach(strip: TerminalStrip, design: Design, count: int) -> tuple[Terminal, ...]:
    """The next `count` boundary terminals of `strip` whose outside end has no conductor yet.

    `_outside` also holds the numbers taken but not yet wired, as in one series call.
    """
    draft = design._engine._design.draft()
    wired = {end for c in draft.records() if isinstance(c, Conductor) for end in (c.a, c.b)}
    free = [
        n
        for n, terminal in sorted(strip._made.items())
        if n not in strip._outside and terminal.outer.id not in wired
    ]
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
