"""The DC half of `dc_supply`: its source pins, nominal voltage and rails."""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Fn
from fransys_author.surface._supply_rails import SupplyRail
from fransys_model.kernel import natural_join
from fransys_model.vocab import RAIL_DEFAULTS, ConductorMark, rail_row
lazy from fransys_author.handles import Port
lazy from fransys_author.surface._device import Device

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.surface.design import Design
    from fransys_model.vocab import Part

PLUS, MINUS, MID = RAIL_DEFAULTS["dc"]
_ZERO = RAIL_DEFAULTS["dc_zero"]
_TWO_OR_THREE = (2, 3)  # names= is (plus, minus) or (plus, minus, mid)


def _marked(design: Design, fn: EngineFn, mark: ConductorMark, given: Port | None) -> Port | None:
    """The pin `given`, else the one pin of `fn` with `mark`; two such pins raise."""
    if given is not None:
        return given
    found = [port for port in fn.ports if design._pairing_facts.mark(port) is mark]
    if len(found) > 1:
        pins = natural_join(port.name for port in found)
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
        found = natural_join(fn.name for fn in pool or functions) or "none"
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
    plus, minus = (_marked(design, fn, mark, given.get(mark)) for mark in (PLUS, MINUS))
    mid = _marked(design, fn, MID, given.get(MID))
    if mid in (plus, minus) and MID not in given:
        mid = None  # a pin the call names as L+ or L- is not also its mid
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
    up, down, *rest = names or ((label, _ZERO) if middle is None else (label, f"-{label}"))
    mid = middle is not None
    rails: list[tuple[SupplyRail, str | Decimal]] = [
        (SupplyRail("plus", plus, up, PLUS, None, rail_row(PLUS, has_mid=mid)), volts),
        (
            SupplyRail("minus", minus, down, MINUS, None, rail_row(MINUS, has_mid=mid)),
            "0" if middle is None else -volts,
        ),
    ]
    if middle is not None:
        rails.append(
            (
                SupplyRail("mid", middle, (*rest, _ZERO)[0], MID, None, rail_row(MID, has_mid=mid)),
                "0",
            )
        )
    return rails
