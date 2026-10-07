"""D5, step 6: each port on a power net and the symbol and text it is drawn with.

The model decides what a net is (`derive.power_kind`) and what it prints (`derive.power_text`);
this reads the answer for every port of the physical net of each declared power net, so a load
pin wired to a 24 V terminal gets it though no `Net` lists it.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.box_power import power_stand
from fransys_layout.stages.types import PowerEnd
from fransys_model.derive import net_of, port_power_kind, port_power_text, power_kind
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import nets

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

# Owner 2026-10-02: A4 supply-only text, A5 "no 180 bending", A6 confirmed; kinds map to keys here
_SYMBOLS = frozendict(
    {
        PowerKind.SUPPLY: "power-supply",
        PowerKind.GROUND: "ground",
        PowerKind.PE: "protective-earth",
    }
)


def power_ends(model: Model) -> tuple[PowerEnd, ...]:
    """The `PowerEnd` of every port on a supply, ground or PE net; the first net's text, by id."""
    found: dict[Id[Any], PowerEnd] = {}
    for net in sorted(nets(model).values(), key=lambda one: one.id):
        if power_kind(model, net.id) is PowerKind.NONE:
            continue
        for port in net.ports:
            physical = net_of(model, port)
            for member in () if physical is None else physical.ports:
                kind = port_power_kind(model, member)
                found.setdefault(member, _end(member, kind, port_power_text(model, member)))
    return tuple(found[port] for port in sorted(found))


def _end(port: Id[Any], kind: PowerKind, text: str | None) -> PowerEnd:
    """The `PowerEnd` of `port` of `kind` printing `text`."""
    return PowerEnd(port=port, kind=kind.value, symbol=_SYMBOLS[kind], text=text)


def port_stand(model: Model, port: Id[Any]) -> int:
    """The width in G of `port`'s power symbol or its text, whichever is wider; 0 off a net."""
    kind = port_power_kind(model, port)
    if kind is PowerKind.NONE:
        return 0
    return power_stand(_SYMBOLS[kind], port_power_text(model, port))
