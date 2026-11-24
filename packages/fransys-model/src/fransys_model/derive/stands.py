"""Fact 5 (PLACEMENT-ENGINE 2.1): the pins that stand a power symbol, with no wire to the rail."""

from typing import TYPE_CHECKING

from fransys_model.derive.connected_ports import boundary_rail_wires
from fransys_model.derive.facts.closure import port_rails
from fransys_model.derive.facts.components import components
from fransys_model.derive.facts.conductor_facts import conductor_ends
from fransys_model.derive.facts.house_settings import export_form_of
from fransys_model.derive.facts.mates import mate_pairs
from fransys_model.derive.facts.rail_source import rail_source_unit
from fransys_model.derive.far_pins import far_pins
from fransys_model.derive.function_scopes import function_scopes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab import Port, PowerKind
from fransys_model.vocab.tables import ports

from .lookups import item_of_port
from .power import drawn_conductors, is_rail_terminal, port_power_kind, port_power_text, wire_pieces

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.vocab.core import Unit

__all__ = ["drawn_stands", "hidden_pins", "power_ends_split", "power_identity", "rail_drawn_by", "stands"]

type Identity = str | tuple[frozenset[str], Id[Unit] | None] | None
type Groups = tuple[tuple[Id[Port], ...], ...]


def power_identity(model: Model, port: Id[Port], kind: PowerKind, text: str | None) -> Identity:
    """What a power symbol of `kind` prints as one potential: its text for a supply, the rails and source unit for a ground, `PE` for earth.

    The one reader: `_rails` joins the ends of a conductor by it before layout, and the drawn-netlist reader joins symbols by it after.
    """
    if kind is PowerKind.SUPPLY:
        return text
    return PowerKind.PE.name if kind is PowerKind.PE else (port_rails(model, port), rail_source_unit(model, port))


def _sets(model: Model, port: Id[Port]) -> frozenset[Id[Unit] | None]:
    """The units of the drawing sets that draw `port`'s function."""
    return frozenset(unit for unit, _ in function_scopes(model, ports(model)[port].function))


def _named(model: Model, kinds: Mapping[Id[Port], PowerKind], one: Id[Port], other: Id[Port]) -> bool:
    """Whether some set unit draws both ends and both print one potential: the symbols carry the conductor (R3699)."""
    ident = [(kinds[p], power_identity(model, p, kinds[p], port_power_text(model, p))) for p in (one, other)]
    return bool(_sets(model, one) & _sets(model, other)) and ident[0] == ident[1]


def _split(model: Model, kinds: Mapping[Id[Port], PowerKind]) -> Groups:
    """The stand pins of each group of conductors and mate pairs, joined by a shared port, that holds one no set draws as one potential."""
    ends = [conductor_ends(model, c) for c in drawn_conductors(model)] + [(one, other) for _, one, other in mate_pairs(model)]
    pairs = [(one, other) for one, other in ends if one in kinds and other in kinds]
    cut = {p for one, other in pairs if not _named(model, kinds, one, other) for p in (one, other)}
    return tuple(group for group in components((), pairs) if cut.intersection(group))


@digest_cached(DIGEST_CACHE_SIZE)
def _rails(model: Model) -> tuple[frozendict[Id[Port], PowerKind], frozendict[Id[Port], tuple[Id[Port], ...]], Groups]:
    """The stands, per rail terminal port the stand pins of its wire piece (a piece with none is left out), and the split groups: the one walk."""
    wired = frozenset(p for w in boundary_rail_wires(model) for p in conductor_ends(model, w))
    kinds: dict[Id[Port], PowerKind] = {}
    drawn_by: dict[Id[Port], tuple[Id[Port], ...]] = {}
    for piece in wire_pieces(model):
        pins = [
            p
            for p in piece.ports
            if port_power_kind(model, p) is not PowerKind.NONE and p not in wired and not is_rail_terminal(model, item_of_port(model, p))
        ]
        kinds.update((p, port_power_kind(model, p)) for p in pins)
        drawn_by.update((p, tuple(pins)) for p in piece.ports if pins and is_rail_terminal(model, item_of_port(model, p)))
    split = _split(model, kinds)
    gone = {p for group in split for p in group}
    kept = {t: left for t, pins in drawn_by.items() if (left := tuple(p for p in pins if p not in gone))}
    return frozendict({p: k for p, k in kinds.items() if p not in gone}), frozendict(kept), split


def stands(model: Model) -> frozendict[Id[Port], PowerKind]:
    """Each port of a rail net, mapped to the net's `PowerKind`; a wire or a signal is absent.

    Built on `power.port_power_kind`, the one rail rule, so a two-port net is never a stand. A port
    of a rail terminal is absent: the terminal is not drawn (POWER-NET). So is a port that ends a
    boundary rail wire: the wire is drawn to the terminal's replica, not also to a symbol (G08-POWER).
    """
    return _rails(model)[0]


def rail_drawn_by(model: Model) -> frozendict[Id[Port], tuple[Id[Port], ...]]:
    """Each rail terminal port, mapped to the pins of its rail net that stand its power symbol (`stands`, whole).

    A flagged terminal draws as the power symbol at each device pin wired to it, so a pin in `drawn_stands` draws it.
    A port that ends a boundary rail wire is kept: its wire is drawn to the terminal's replica, and the inside pins stand its symbol.
    """
    return _rails(model)[1]


def power_ends_split(model: Model) -> Groups:
    """The pins of each group of power conductors that no drawing set draws as one potential: drawn as nets, never as symbols.

    Conductors that share a port are one group, so no pin keeps a symbol for one conductor and a wire for another.
    A mate pair is a connection like a conductor. Both are carried by symbols only when some set unit draws both ends under one `power_identity`.
    A mated pin whose partner stands in another set is a net: it draws the mate's OFF stub, never a bare power symbol.
    """
    return _rails(model)[2]


def drawn_stands(model: Model) -> frozendict[Id[Port], PowerKind]:
    """`stands` as a drawing sheet draws them: with `[export] hide_pe` the PE ports are left out.

    `stands` itself stays whole for ratings, rail reach and series-parallel, which are not drawings.
    """
    kept = stands(model)
    if not export_form_of(model).hide_pe:
        return kept
    return frozendict({port: kind for port, kind in kept.items() if kind is not PowerKind.PE})


def hidden_pins(model: Model) -> frozenset[Id[Port]]:
    """The stand ports `drawn_stands` leaves off whose pin no drawn conductor reaches: a pin the sheets do not show."""
    left = stands(model).keys() - drawn_stands(model).keys()
    return frozenset(port for port in left if not far_pins(model, [port]))
