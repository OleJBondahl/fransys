"""The default symbol of a function: a first-match table, and the authored choices over it.

A copy of the schematic engine's rule (`conventions/symbols.py`, `stages/resolve._symbol_for`),
kept until the flip (SB9). A kind row, then a state row, as the engine's two lookups combined.
"""

from typing import TYPE_CHECKING, NamedTuple

from fransys_model.layout import SymbolChoice, layout_of

from .placement_ids import symbol_key
from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Part

__all__ = ["Facts", "symbol_for"]


class Facts(NamedTuple):
    """What the table reads of one function; a missing value is `None`."""

    kind: str
    rest: str | None
    protection_type: str | None
    gender: str | None
    operated_by: str | None
    actuator: bool
    port_shape: str = "other"


def port_shape(names: Collection[str]) -> str:
    """`three-phase` when every port name is a motor terminal's, else `other` (R479)."""
    return "three-phase" if names and set(names) <= MOTOR_MAP.keys() else "other"


NO_MAP: frozendict[str, str] = frozendict(dict[str, str]())
# A motor (Ruling 68 A1); the symbol's ports are lower case.
MOTOR_MAP: frozendict[str, str] = frozendict(
    {**{n: n.lower()[0] for n in ("U", "V", "W", "U1", "V1", "W1")}, "PE": "pe"}
)


class Row(NamedTuple):
    """A symbol, the facts it needs (all must equal), and its port map."""

    symbol: str
    when: tuple[tuple[str, str | None], ...]
    port_map: frozendict[str, str] = NO_MAP


def _kind(symbol: str, kind: str, *more: tuple[str, str | None]) -> Row:
    return Row(symbol, (("kind", kind), *more))


def _operated(symbol: str, operator: str, rest: str) -> Row:
    return _kind(symbol, "switch", ("operated_by", operator), ("rest", rest))


def _by_type(symbol: str, value: str) -> Row:
    return _kind(symbol, "protection", ("protection_type", value))


_APART = ("actuator", "apart")
_REST = ("rest", "rest")
_OPERATED = ("rest", "operated")

TABLE: tuple[Row, ...] = (
    _kind("break-contact-positive-opening", "switch", _APART, ("operated_by", "mushroom"), _REST),
    _kind("make-contact", "switch", _APART, _OPERATED),
    _kind("break-contact", "switch", _APART, _REST),
    _operated("push-button", "push", "operated"),
    _operated("push-button-break", "push", "rest"),
    _operated("emergency-stop", "mushroom", "rest"),
    _operated("selector-make", "turn", "operated"),
    _operated("selector-break", "turn", "rest"),
    _operated("position-switch-make", "position", "operated"),
    _operated("position-switch-break", "position", "rest"),
    _kind("make-contact", "switch", _OPERATED),
    _kind("break-contact", "switch", _REST),
    _kind("make-contact", "generic", _OPERATED),
    _kind("break-contact", "generic", _REST),
    _by_type("circuit-breaker", "none"),
    _by_type("fuse", "fuse"),
    _by_type("circuit-breaker", "mcb"),
    _by_type("circuit-breaker", "motor_breaker"),
    _by_type("thermal-overload", "overload"),
    _by_type("rcd", "rcd"),
    _kind("operating-device", "coil"),
    _kind("contact-female", "connector", ("gender", "female")),
    _kind("contact-male", "connector", ("gender", "male")),
    _kind("contact", "connector"),
    _kind("change-over-contact", "contact_co"),
    _kind("break-contact", "contact_nc"),
    _kind("make-contact", "contact_no"),
    _kind("circuit-breaker", "protection"),
    _kind("plc-channel", "plc_channel"),
    _kind("make-contact", "switch"),
    # The part-less terminal names its outside port `external`; the symbol's is `s`.
    Row("terminal", (("kind", "terminal"),), frozendict({"external": "s"})),
    # A motor (Ruling 68 A1); the symbol's ports are lower case.
    Row(
        "motor-3ph-pe",
        (("kind", "actuator"), ("port_shape", "three-phase")),
        MOTOR_MAP,
    ),
)


def _subject(facts: Facts) -> dict[str, str | None]:
    return {
        "kind": facts.kind,
        "rest": facts.rest or "none",
        "protection_type": facts.protection_type or "none",
        "gender": facts.gender or "none",
        "operated_by": facts.operated_by or "none",
        "actuator": "lead" if facts.actuator else "apart",
        "port_shape": facts.port_shape,
    }


def default_row(facts: Facts) -> Row | None:
    """The first row of `TABLE` whose facts all equal `facts`'; `None` draws a labelled box."""
    subject = _subject(facts)
    return next((r for r in TABLE if all(subject[k] == v for k, v in r.when)), None)


def _choices_at(
    model: Model, function: Function, part: Id[Part] | None
) -> tuple[list[SymbolChoice], ...]:
    """The authored choices for `function` by specificity: function (or template), part, kind."""
    found = list(layout_of(model, SymbolChoice).values())
    own = [c for c in found if c.function == function.id]
    from_template = [
        c for c in found if function.template is not None and c.template == function.template
    ]
    return (
        own or from_template,
        [c for c in found if part is not None and c.part == part],
        [c for c in found if c.kind is function.kind],
    )


def symbol_for(
    model: Model, function: Function, part: Id[Part] | None, facts: Facts
) -> tuple[str | None, frozendict[str, str]]:
    """The symbol key (`None`: a box) and the port map of `function`: choice, then the table."""
    for level in _choices_at(model, function, part):
        if len(level) > 1:
            refuse(
                f"function {function.id}",
                "several symbol choices of one specificity apply",
                symbol_key(model, function.id),
            )
        if level:
            return level[0].symbol, level[0].port_map
    row = default_row(facts)
    if row is None:
        return None, NO_MAP
    return row.symbol, row.port_map
