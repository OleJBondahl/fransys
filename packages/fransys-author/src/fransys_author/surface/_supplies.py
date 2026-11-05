"""Surface mixin for supplies and rails: `ac_supply`, `dc_supply` and their rail handles."""

from typing import TYPE_CHECKING, cast
lazy from collections.abc import Sequence
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.surface._supplies_dc import (
    MID,
    MINUS,
    PLUS,
    _bare_facts,
    _dc_facts,
    _dc_rails,
    _forbid_voltage,
    _source,
    rail_row,
)
from fransys_author.surface._supply_rails import AcSupply, DcSupply, SupplyRail
from fransys_author.surface._wire import _port
from fransys_model.vocab import RAIL_DEFAULTS, ConductorMark
lazy from fransys_author.handles import Port, Terminal
lazy from fransys_author.surface._device import Device
lazy from fransys_author.surface._handles import Fn

if TYPE_CHECKING:
    from fransys_author.surface.design import Design

_AC = cast("tuple[tuple[ConductorMark, int], ...]", RAIL_DEFAULTS["ac"])
_NEUTRAL = cast("ConductorMark", RAIL_DEFAULTS["ac_neutral"])
_ONE_OR_THREE = (1, 3)


def _declare(
    design: Design,
    name: str,
    current: str,
    rails: Sequence[tuple[SupplyRail, str | Decimal]],
) -> None:
    """Write the supply system, then one power net per rail named after its potential."""
    specs = {rail.potential: (volts, rail.phase) for rail, volts in rails}
    design._engine.supply(
        name,
        current=current,
        rails=specs,
        pins=[rail.pin for rail, _ in rails],
    )
    for rail, _ in rails:
        design._engine.net(rail.potential, rail.pin, cls="power", potential=rail.potential)


def _refuse_branch(design: Design, name: str, pins: tuple[Port, ...]) -> None:
    """A pin of a fuse or breaker feeds a branch; it is no source (authoring guide, author-0055)."""
    for pin in pins:
        if design._pairing_facts.protective(pin):
            msg = (
                f"ac_supply {name!r}: pin {pin.name} of {pin.key[0]} belongs to a fuse or "
                "breaker, and a fused branch is not a supply. Start the branch as a second series "
                "from the common feed, or wire a branch looped at its line screws with "
                "d.series(pin, pin, wire=...), one hop per pole"
            )
            raise AuthorError(msg)


def _phases(design: Design, name: str, phases: tuple[Port | Terminal, ...]) -> tuple[Port, ...]:
    """The phase pins as ports; only one or three phases make a supply."""
    if len(phases) not in _ONE_OR_THREE:
        msg = f"ac_supply {name!r} takes 1 or 3 phase pins, not {len(phases)}"
        raise AuthorError(msg)
    ports = tuple(_port(design, pin) for pin in phases)
    _refuse_branch(design, name, ports)
    return ports


def _ac_names(phases: int, names: tuple[str, ...] | None, *, has_n: bool) -> tuple[str, ...]:
    """The printed rail names: L1.. then N by default; `names=` must give one per pin."""
    default = tuple(mark.value for mark, _ in _AC[:phases]) + ((_NEUTRAL.value,) if has_n else ())
    if names is None:
        return default
    if len(names) != len(default):
        msg = f"names= is one per phase pin, then one for n: expected {len(default)}, not {names!r}"
        raise AuthorError(msg)
    return tuple(names)


class Supplies:
    """The supply calls of `Design`: `ac_supply` and `dc_supply`."""

    def ac_supply(
        self: "Design",
        name: str,
        voltage: str | int | Decimal,
        *phases: Port | Terminal,
        n: Port | Terminal | None = None,
        names: tuple[str, ...] | None = None,
    ) -> AcSupply:
        """Declare an AC supply on 1 or 3 phase pins in phase order, and `n`; rails `ac.L1`.

        `voltage` is each phase's RMS to the star point; `names=` renames the rails, one per pin.
        Does not read the voltage from a part.
        """
        pins = _phases(self, name, phases)
        printed = _ac_names(len(pins), names, has_n=n is not None)
        rails = [
            (SupplyRail(mark.value, pin, printed[i], mark, phase, rail_row(mark)), str(voltage))
            for i, ((mark, phase), pin) in enumerate(zip(_AC, pins, strict=False))
        ]
        if n is not None:
            neutral = _port(self, n)
            _refuse_branch(self, name, (neutral,))
            rail = SupplyRail(_NEUTRAL.value, neutral, printed[-1], _NEUTRAL, None, rail_row(_NEUTRAL))
            rails.append((rail, "0"))
        _declare(self, name, "ac", rails)
        return AcSupply(name, (rail for rail, _ in rails))

    def dc_supply(  # noqa: PLR0913 -- the call's own spec signature [public keyword API kept, decision 0444]
        self: "Design",
        name: str,
        source: Device | Fn | None = None,
        *,
        plus: Port | Terminal | None = None,
        minus: Port | Terminal | None = None,
        mid: Port | Terminal | None = None,
        voltage: str | int | Decimal | None = None,
        names: tuple[str, ...] | None = None,
    ) -> DcSupply:
        """Declare a DC supply from `source`'s L+, L- pins and voltage, or from the pins given.

        Does not find a pin by name: with no `source` the pins and `voltage=` are required.
        """
        given: dict[ConductorMark, Port | None] = {
            PLUS: None if plus is None else _port(self, plus),
            MINUS: None if minus is None else _port(self, minus),
        }
        if mid is not None:
            given[MID] = _port(self, mid)
        if source is None:
            found = _bare_facts(name, given, voltage)
        else:
            label, fn = _source(self, source, given)
            _forbid_voltage(self, label, fn, voltage)
            found = _dc_facts(self, f"dc_supply {name!r}: {label}.{fn.name}", fn, given, voltage)
        rails = _dc_rails(found[3], found[:3], names)
        _declare(self, name, "dc", rails)
        return DcSupply(name, (rail for rail, _ in rails))
