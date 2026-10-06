"""Surface mixin for supplies and rails: `ac_supply`, `dc_supply` and their rail handles (EA6)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import End, Ends
from fransys_author.surface._wire import _port
from fransys_model.vocab import ConductorMark, Earthing
lazy from fransys_author.handles import Port, Terminal
lazy from fransys_author.surface._device import Device

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_author.handles import Fn as EngineFn
    from fransys_author.surface.design import Design
    from fransys_model.vocab import Part

PLUS, MINUS, MID = ConductorMark.L_PLUS, ConductorMark.L_MINUS, ConductorMark.M
_AC = ((ConductorMark.L1, 0), (ConductorMark.L2, 120), (ConductorMark.L3, 240))
_ONE_OR_THREE = (1, 3)
_TWO_OR_THREE = (2, 3)  # names= is (plus, minus) or (plus, minus, mid)


@dataclass(frozen=True)
class SupplyRail:
    """One rail of a supply: its source pin, the potential it carries and its conductor mark.

    Does not wire itself: it stands in a `series` as a one-conductor element.
    """

    name: str
    pin: Port
    potential: str
    mark: ConductorMark
    phase: int | None

    def _series_width(self) -> int | None:
        return 1

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        end = (End(self.pin, self.mark),)
        return Ends(end, end)


class _Rails:
    """The rails of one supply by attribute; a misspelt rail raises and lists the real ones."""

    def __init__(self, name: str, rails: Iterable[SupplyRail]) -> None:
        self._name, self._rails = name, tuple(rails)
        self.__dict__.update({rail.name: rail for rail in self._rails})

    if not TYPE_CHECKING:  # the subclass declares its rails; ty must see no catch-all

        def __getattr__(self, name: str) -> SupplyRail:
            """The rail `name`.

            Does not guess: an unknown rail raises and lists the rails.
            """
            if name.startswith("_"):
                raise AttributeError(name)
            names = ", ".join(rail.name for rail in self._rails)
            msg = f"no rail {name!r}; rails: {names}"
            raise AuthorError(msg)


class AcSupply(_Rails):
    """An AC supply: `L1`, `L2`, `L3` and `N` when it was given one.

    Does not hold a voltage of its own: each rail's potential carries the declared voltage.
    """

    L1: SupplyRail
    L2: SupplyRail
    L3: SupplyRail
    N: SupplyRail

    def _series_width(self) -> int | None:
        return len(self._rails)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        ends = tuple(End(rail.pin, rail.mark) for rail in self._rails)
        return Ends(ends, ends)


class DcSupply(_Rails):
    """A DC supply: `plus`, `minus` and `mid` when the source has an M conductor.

    Does not stand in a series itself: each of its rails does.
    """

    plus: SupplyRail
    minus: SupplyRail
    mid: SupplyRail


def _declare(
    design: Design,
    name: str,
    current: str,
    rails: Sequence[tuple[SupplyRail, str | Decimal]],
    earthing: Earthing,
) -> None:
    """Write the supply system, then one power net per rail named after its potential."""
    if not isinstance(earthing, Earthing):
        msg = f"earthing must be Earthing.EARTHED or Earthing.IT, not {earthing!r}"
        raise AuthorError(msg)
    specs = {rail.potential: (volts, rail.phase) for rail, volts in rails}
    design._engine.supply(name, current=current, rails=specs, earthing=earthing.value)
    for rail, _ in rails:
        design._engine.net(rail.potential, rail.pin, cls="power", potential=rail.potential)


def _marked(design: Design, fn: EngineFn, mark: ConductorMark, given: Port | None) -> Port | None:
    """The pin `given`, else the one pin of `fn` with `mark`; two such pins raise."""
    if given is not None:
        return given
    found = [port for port in fn.ports if design._pairing_facts.mark(port) is mark]
    if len(found) > 1:
        pins = ", ".join(sorted(port.name for port in found))
        msg = f"{fn.name!r} has several {mark.value} pins ({pins}): pass plus= and minus="
        raise AuthorError(msg)
    return found[0] if found else None


def _source(
    design: Design, source: Device | Fn, given: dict[ConductorMark, Port | None]
) -> tuple[str, EngineFn]:
    """The label and engine function a `dc_supply` source stands for."""
    if isinstance(source, Fn):
        return source._label, source._fn
    functions = source._item.functions
    fits = [
        fn
        for fn in functions
        if all(_marked(design, fn, mark, pin) is not None for mark, pin in given.items())
    ]
    pool = fits or (list(functions) if len(functions) == 1 else [])
    if len(pool) != 1:
        found = ", ".join(sorted(fn.name for fn in pool or functions)) or "none"
        msg = f"{source._label} needs exactly one function with L+ and L- pins; candidates: {found}"
        raise AuthorError(msg)
    return source._label, pool[0]


def _nominal(design: Design, fn: EngineFn) -> Decimal | None:
    template = design._pairing_facts.function_template(fn)
    part = cast("Part", design.library.record_of(template.part))
    operating = design._engine.operating((part.manufacturer, part.mpn), template.name)
    return None if operating is None else operating.nominal_voltage_v


def _forbid_voltage(
    design: Design, label: str, fn: EngineFn, voltage: str | int | Decimal | None
) -> None:
    """A source whose part states its nominal voltage takes no `voltage=`."""
    nominal = _nominal(design, fn)
    if nominal is not None and voltage is not None:
        msg = f"{label} states {format(nominal.normalize(), 'f')} V: drop voltage="
        raise AuthorError(msg)


def _dc_facts(
    design: Design,
    where: str,
    fn: EngineFn,
    given: dict[ConductorMark, Port | None],
    voltage: str | int | Decimal | None,
) -> tuple[Port, Port, Port | None, Decimal]:
    """The L+, L- and M pins and the voltage of `fn`; a missing one raises by name."""
    plus, minus, mid = (_marked(design, fn, mark, given.get(mark)) for mark in (PLUS, MINUS, MID))
    volts = _nominal(design, fn) if voltage is None else Decimal(str(voltage))
    if plus is None or minus is None or volts is None:
        facts = (("L+ pin", plus), ("L- pin", minus), ("nominal voltage", volts))
        msg = f"{where} lacks {', '.join(text for text, found in facts if found is None)}"
        raise AuthorError(msg)
    return plus, minus, mid, volts


def _bare_facts(
    name: str, given: dict[ConductorMark, Port | None], voltage: str | int | Decimal | None
) -> tuple[Port, Port, Port | None, Decimal]:
    """The facts of a `dc_supply` with no source: `plus=`, `minus=` and `voltage=` all given."""
    plus, minus = given[PLUS], given[MINUS]
    facts = (("plus=", plus), ("minus=", minus), ("voltage=", voltage))
    if plus is None or minus is None or voltage is None:
        missing = ", ".join(text for text, found in facts if found is None)
        msg = f"dc_supply {name!r} has no source, so it needs {missing}"
        raise AuthorError(msg)
    return plus, minus, given.get(MID), Decimal(str(voltage))


def _dc_rails(
    volts: Decimal, pins: tuple[Port, Port, Port | None], names: tuple[str, ...] | None
) -> list[tuple[SupplyRail, str | Decimal]]:
    """Without a mid, minus is 0 V; with one, mid is 0 V and minus is -volts."""
    if names is not None and len(names) not in _TWO_OR_THREE:
        msg = f"names= is (plus, minus) or (plus, minus, mid), not {names!r}"
        raise AuthorError(msg)
    plus, minus, middle = pins
    label = f"{format(volts.normalize(), 'f')}V"
    up, down, *rest = names or ((label, "0V") if middle is None else (label, f"-{label}"))
    rails: list[tuple[SupplyRail, str | Decimal]] = [
        (SupplyRail("plus", plus, up, PLUS, None), volts),
        (SupplyRail("minus", minus, down, MINUS, None), "0" if middle is None else -volts),
    ]
    if middle is not None:
        rails.append((SupplyRail("mid", middle, (*rest, "0V")[0], MID, None), "0"))
    return rails


def _phases(design: Design, name: str, phases: tuple[Port | Terminal, ...]) -> tuple[Port, ...]:
    """The phase pins as ports; only one or three phases make a supply."""
    if len(phases) not in _ONE_OR_THREE:
        msg = f"ac_supply {name!r} takes 1 or 3 phase pins, not {len(phases)}"
        raise AuthorError(msg)
    return tuple(_port(design, pin) for pin in phases)


def _ac_names(phases: int, names: tuple[str, ...] | None, *, has_n: bool) -> tuple[str, ...]:
    """The printed rail names: L1.. then N by default; `names=` must give one per pin."""
    default = tuple(mark.value for mark, _ in _AC[:phases]) + (("N",) if has_n else ())
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
        earthing: Earthing = Earthing.EARTHED,
    ) -> AcSupply:
        """Declare an AC supply on 1 or 3 phase pins in phase order, and `n`; rails `ac.L1`.

        `voltage` is each phase's RMS to the star point; `names=` renames the rails, one per pin.
        Does not read the voltage from a part.
        """
        pins = _phases(self, name, phases)
        printed = _ac_names(len(pins), names, has_n=n is not None)
        rails = [
            (SupplyRail(mark.value, pin, printed[i], mark, phase), str(voltage))
            for i, ((mark, phase), pin) in enumerate(zip(_AC, pins, strict=False))
        ]
        if n is not None:
            rails.append((SupplyRail("N", _port(self, n), printed[-1], ConductorMark.N, None), "0"))
        _declare(self, name, "ac", rails, earthing)
        return AcSupply(name, (rail for rail, _ in rails))

    def dc_supply(  # noqa: PLR0913 -- the call's own spec signature (EA6, EA15)
        self: "Design",
        name: str,
        source: Device | Fn | None = None,
        *,
        plus: Port | Terminal | None = None,
        minus: Port | Terminal | None = None,
        mid: Port | Terminal | None = None,
        voltage: str | int | Decimal | None = None,
        names: tuple[str, ...] | None = None,
        earthing: Earthing = Earthing.EARTHED,
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
        _declare(self, name, "dc", rails, earthing)
        return DcSupply(name, (rail for rail, _ in rails))
