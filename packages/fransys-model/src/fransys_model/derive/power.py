"""What a physical net is on the drawing: supply, ground, protective earth or none (model-0117)."""

from fransys_model.derive.facts.closure import PhysicalNet, joined_nets, net_of, required_groups
from fransys_model.derive.facts.conductor_facts import conductor_ends, is_bridge
from fransys_model.derive.facts.house_settings import export_form_of
from fransys_model.derive.facts.potentials import pe_firsts, physical_potentials
from fransys_model.derive.facts.protected import protected_by
from fransys_model.derive.facts.rail_source import rail_source_unit
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.elecdef import Current
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab import Item, Net, Port, PowerKind
from fransys_model.vocab.tables import conductors, nets, rail_groups, supply_of_potential
lazy from fransys_model.vocab.connectivity import Conductor

from .facts.net_facts import net_potential
from .instance_tag import unit_system_designation
from .lookups import item_of_port
from .order import NaturalKey, natural_key
from .tag_text import item_tag_text

_WIRE_PORTS = 2  # a physical net of this many ports is one wire, not a rail


def _potential_kind(model: Model, potential: str) -> PowerKind:
    """A DC rail's kind by `max_v`: 0 V ground, else supply; an AC or unsupplied one `NONE`."""
    supply = supply_of_potential(model, potential)
    if supply is None or supply.current is not Current.DC:
        return PowerKind.NONE
    return PowerKind.GROUND if supply.rails[potential].max_v == 0 else PowerKind.SUPPLY


@digest_cached(DIGEST_CACHE_SIZE)
def wire_pieces(model: Model) -> tuple[PhysicalNet, ...]:
    """The physical nets split where a bridge joined them: the ports one wire, link or mate joins (G08-POWER, R3641).

    The one reader of "joined by wires" for power: the kind, the text and the stands count these, never a bridge,
    except one between two flagged rail terminals: a rail is declared, so its terminals are one rail.
    """
    groups, wires = required_groups(model), conductors(model)
    kept = [g for g, c in zip(groups, wires, strict=False) if not is_bridge(model, c) or is_rail_bond(model, c)]
    return joined_nets(model, [*kept, *groups[len(wires) :]])


@digest_cached(DIGEST_CACHE_SIZE)
def _piece_first(model: Model) -> frozendict[Id[Port], Id[Port]]:
    """Each port's wire piece, as the piece's first port."""
    return frozendict({port: piece.ports[0] for piece in wire_pieces(model) for port in piece.ports})


def _agreed(kinds: set[PowerKind]) -> PowerKind:
    """The one kind `kinds` holds, else `NONE`."""
    return kinds.pop() if len(kinds) == 1 else PowerKind.NONE


def _piece_kind(model: Model, piece: PhysicalNet, whole: PhysicalNet) -> PowerKind:
    """The kind of wire `piece` of physical net `whole`: `NONE` for a wire, else `PE`, else the one potential's, read on the whole net.

    A wire is a piece of two ports or a lone pin a bridge cut off `whole`; a PE terminal's two sides are a link, which stays.
    """
    link = whole.ports[0] in pe_firsts(model) and len({item_of_port(model, p) for p in piece.ports}) == 1
    cut_off = len(piece.ports) < _WIRE_PORTS and len(piece.ports) < len(whole.ports)
    if not link and (len(piece.ports) == _WIRE_PORTS or cut_off):
        return PowerKind.NONE
    if whole.ports[0] in pe_firsts(model):
        return PowerKind.PE
    potentials = tuple(physical_potentials(model, whole))
    return _potential_kind(model, potentials[0]) if len(potentials) == 1 else PowerKind.NONE


@digest_cached(DIGEST_CACHE_SIZE)
def _kinds(model: Model) -> frozendict[Id[Port], PowerKind]:
    """Each wire piece's `_piece_kind` by first port."""
    pieces = ((piece, net_of(model, piece.ports[0])) for piece in wire_pieces(model))
    return frozendict({piece.ports[0]: _piece_kind(model, piece, whole) for piece, whole in pieces if whole is not None})


def port_power_kind(model: Model, port: Id[Port]) -> PowerKind:
    """The `PowerKind` of the wire piece of `port`; `NONE` when `port` is not in `model`.

    A load pin wired to a 24 V terminal gets the kind of that net though no `Net` lists it; a pin
    only a bridge joins to the rail gets none. Cost: O(1) once per model digest, like `port_rails`.
    """
    first = _piece_first(model).get(port)
    return PowerKind.NONE if first is None else _kinds(model).get(first, PowerKind.NONE)


def power_kind(model: Model, net: Id[Net]) -> PowerKind:
    """The `PowerKind` of declared `net`, read from its physical net, never from its name.

    A physical net holding a net of class `PE` is `PE`, supplied or not. Otherwise its one potential is
    looked up in the supplies: a DC rail above or below 0 V is `SUPPLY`, a DC rail at 0 V is
    `GROUND`. An AC rail, a potential in no supply, no potential, or two potentials on one
    physical net are `NONE`, as is a net whose ports fall in physical nets of different kinds.
    A wire piece of two ports, links counted and bridges never, is `NONE` whatever its
    potential: a wire, not a rail; it keeps the potential.
    A DC supply that declares no 0 V rail leaves its 0 V net `NONE`: declare it.

    Raises:
        KeyError: `net` is not a declared `Net` of `model`.
    """
    declared = nets(model)[net]
    return _agreed({port_power_kind(model, port) for port in declared.ports})


def _net_whole_kind(model: Model, declared: Net) -> PowerKind:
    """The one kind of the whole physical nets of declared `declared`, else `NONE`: what its text is read on, wire pieces and bridges aside."""
    return _agreed({_piece_kind(model, whole, whole) for port in declared.ports if (whole := net_of(model, port)) is not None})


def _base_text(model: Model, net: Id[Net]) -> str | None:
    """The name a supply or ground net prints before any source tag; `None` for `PE` and `NONE`.

    `Net.name`, else `Net.potential` (which carries the sign of a negative rail, `-15V`). A supply net
    behind a protective device adds the tag of the nearest one, `24V -F2` (`protected_by`, G08-POWER).
    """
    declared = nets(model)[net]
    kind = _net_whole_kind(model, declared)
    if kind not in {PowerKind.SUPPLY, PowerKind.GROUND}:
        return None
    name = declared.name if declared.name is not None else net_potential(model, net)
    physical = net_of(model, declared.ports[0])
    device = None if kind is PowerKind.GROUND or name is None or physical is None else protected_by(model).get(physical.ports[0])
    return name if device is None else f"{name} {item_tag_text(model, device, unit=item_unit(model, device))}"


def _printed(model: Model, text: str | None, kind: PowerKind, port: Id[Port]) -> str | None:
    """`text` as the symbol at `port` prints it: behind the declaring unit's tag where `rail_source_unit` names one (R2589).

    A ground symbol prints only then.
    """
    unit = rail_source_unit(model, port)
    tag = None if unit is None else unit_system_designation(model, unit)
    if text is None:
        return None
    if tag is None:
        return text if kind is PowerKind.SUPPLY else None
    return f"{text} {tag}"


def power_text(model: Model, net: Id[Net]) -> str | None:
    """The text a power symbol of declared `net` prints, or `None` when it prints none.

    `SUPPLY` prints `Net.name`, else `Net.potential`, with the nearest protective device's tag (`24V -F2`).
    Where the cabinet of the net's first port is fed that potential by two or more unbonded supplies, the
    symbol adds the tag of the declaring unit (`24V -U1`), and `GROUND` prints it too (`GND -U1`, R2589).
    Otherwise `GROUND`, `PE` and `NONE` print none.
    """
    kind = power_kind(model, net)
    text = None if kind is PowerKind.NONE else _base_text(model, net)
    return None if text is None else _printed(model, text, kind, nets(model)[net].ports[0])


def _text_order(model: Model, net: Net) -> tuple[NaturalKey, Id[Net]]:
    """First-wins order of declared nets: printed name or potential, naturally, then id."""
    return natural_key(net.name or net_potential(model, net.id) or ""), net.id


@digest_cached(DIGEST_CACHE_SIZE)
def _texts(model: Model) -> frozendict[Id[Port], str | None]:
    """Each power physical net (the whole, bridges joined) base text by its first port: the first declared net's, by net id."""
    texts: dict[Id[Port], str | None] = {}
    for net in sorted(nets(model).values(), key=lambda n: _text_order(model, n)):
        if _net_whole_kind(model, net) is PowerKind.NONE:
            continue
        for port in net.ports:
            if (physical := net_of(model, port)) is not None:
                texts.setdefault(physical.ports[0], _base_text(model, net.id))
    return frozendict(texts)


def port_power_text(model: Model, port: Id[Port]) -> str | None:
    """The text the power symbol at `port` prints: the text of its physical net as `power_text` prints it at `port`, else `None`.

    A load pin wired to a 24 V terminal prints that net's text. Cost: O(1) once per model digest.
    """
    physical, kind = net_of(model, port), port_power_kind(model, port)
    return None if physical is None or kind is PowerKind.NONE else _printed(model, _texts(model).get(physical.ports[0]), kind, port)


@digest_cached(DIGEST_CACHE_SIZE)
def _flagged(model: Model) -> frozenset[Id[Item]]:
    """The terminals of every declared `RailGroup`."""
    return frozenset(terminal for group in rail_groups(model).values() for terminal in group.terminals)


def is_rail_terminal(model: Model, terminal: Id[Item]) -> bool:
    """Whether `terminal` is a rail terminal: true exactly when its group carries the flag.

    A rail terminal draws no symbol: its pins show the rail's power symbol. An unflagged
    terminal, bridged or not, and any item that is not a terminal are `False`.
    """
    return terminal in _flagged(model)


def is_pe_conductor(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether an end of `conductor` is a pin on the PE net, joined however (earth, bridge, strip run, cable core).

    The one home of what the hide-PE option leaves off the drawing sheets.
    """
    return any(port_power_kind(model, p) is PowerKind.PE for p in conductor_ends(model, conductor))


def is_rail_bond(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether both ends of `conductor` are flagged rail terminals: two rails of one potential bonded, a link and never a wire (R3310).

    The one home of "bond" for the drawing sheets; POWER-NET leaves it off like a bridge.
    """
    return all(is_rail_terminal(model, item_of_port(model, p)) for p in conductor_ends(model, conductor))


@digest_cached(DIGEST_CACHE_SIZE)
def drawn_conductors(model: Model) -> frozenset[Id[Conductor]]:
    """The conductors a drawing may join: every one but a bridge or a rail bond (the terminal table carries bridges).

    With `[export] hide_pe` a PE conductor is left out too. The one source of what drawing reads; the list sites read `conductors` whole.
    """
    hide = export_form_of(model).hide_pe
    return frozenset(c for c in conductors(model) if not (is_bridge(model, c) or is_rail_bond(model, c) or (hide and is_pe_conductor(model, c))))
