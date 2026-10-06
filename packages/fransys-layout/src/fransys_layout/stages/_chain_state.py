"""The pole and group types of chain discovery, and the state its phases hand on (chains.py)."""

import dataclasses
import enum
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections import Counter
    from collections.abc import Mapping

    from .types import Cell, Connection, DrawnFunction, FunctionSpec, Handle

# A pole's id: `(function, index)`, or `(a, b, name)` for a mate pole, `(a, b, "edge")` and
# `(function, edge function, "off")` for the two stand-in poles.
type _PoleId = tuple[Handle | int | str, ...]

# A link, or a function's through path, joins exactly two ports.
_LINK_PORTS = 2


class _Synthetic(enum.Enum):
    """What a pole the stage invents (not a function's own) is labelled with."""

    MATE = enum.auto()  # a mated pin pair, or a pin mated across a unit edge
    OFF = enum.auto()  # the item marker of a pin's pole to the edge
    PIN = enum.auto()  # the kind of that pole


# Row markers of a pin face to face across a unit edge (private to the columns pass).
_EDGE_FACE = "edge"


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Pole:
    function: Any  # the function that orders the pole, and the column key's
    functions: Any  # every function the row shows for this pole
    index: Any
    ports: Any
    inn: Any
    item: Any
    kind: Any
    terminal: bool


@dataclasses.dataclass(slots=True, eq=False)
class _Group:
    """The chains one column is built from; `bottom` packs shorter lanes to the column's end."""

    chains: list[list[_PoleId]]
    bottom: bool = False


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Poles:
    """What the poles phase leaves for the later phases."""

    poles: dict[_PoleId, _Pole]
    pole_of_port: dict[Handle, _PoleId]
    port_function: dict[Handle, Handle]
    split: dict[Handle, Handle]  # R7 B5: an in-line terminal's second wire -> its port
    throw_pairs: list[tuple[Handle, Handle]]  # S13: a changeover's throw on, and off, its pole
    edge_poles: set[_PoleId]


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Nets:
    """The nets over the ports of the functions: `members` loses the hidden side ports later."""

    net_of: dict[Handle, Handle]
    members: dict[Handle, list[Handle]]
    net_size: Counter[Handle]  # every port of a net, the hidden side ports too


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Links:
    """What the chain walk follows: the nets, the poles by port, and S13's detached throws."""

    members: dict[Handle, list[Handle]]
    net_of: dict[Handle, Handle]
    pole_of_port: dict[Handle, _PoleId]
    detached: set[Handle]
    connections: tuple[Connection, ...]

    def partner(self, p: Handle) -> Handle | None:
        """The port a link joins `p` to, when that port is on a pole and no throw detached it."""
        net = self.members[self.net_of[p]]
        if len(net) != _LINK_PORTS:
            return None
        other = net[0] if net[1] == p else net[1]
        if p in self.detached or other in self.detached:
            return None
        return other if other in self.pole_of_port else None

    def wires_on(self, pole: _Pole) -> int:
        """The conductors that end on a port of `pole`."""
        return sum(1 for c in self.connections if c.a.port in pole.ports or c.b.port in pole.ports)


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Reading:
    """What the direction pass over the walks reads."""

    poles: dict[_PoleId, _Pole]
    edge_poles: set[_PoleId]
    port_function: dict[Handle, Handle]
    specs: Mapping[Handle, FunctionSpec]
    rank_of: Mapping[Handle, int]
    tie_key: Mapping[Handle, tuple[str, ...]]
    port_side: dict[Handle, str | None]
    strip_entry: dict[str, str | None]


@dataclasses.dataclass(slots=True, eq=False)
class _Walks:
    """The chains the walk finds, how each ends, which functions turn, and the bundles."""

    chains: list[list[_PoleId]] = dataclasses.field(default_factory=list)
    ends_of: dict[tuple[_PoleId, ...], tuple[Handle, Handle]] = dataclasses.field(
        default_factory=dict
    )
    flipped: set[Handle] = dataclasses.field(default_factory=set)
    # D8: edge poles entered from the edge
    edge_top: set[_PoleId] = dataclasses.field(default_factory=set)
    # D1: a directed pole against its chain
    against: set[Handle] = dataclasses.field(default_factory=set)
    # D1: a directed pole along its chain
    along: set[Handle] = dataclasses.field(default_factory=set)
    upper_of: dict[_PoleId, Handle] = dataclasses.field(default_factory=dict)
    turned: set[Handle] = dataclasses.field(default_factory=set)
    bundles: list[list[list[_PoleId]]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Sides:
    """The side elements the nets phase finds and the ports they hide."""

    sides: dict[_PoleId, list[Handle]]
    side_info: dict[Handle, tuple[bool, bool]]  # side function -> (flip, low)
    carrier_of: dict[Handle, Handle]  # side function -> the function whose cell it stands beside
    hidden: set[Handle]
    side_ports: dict[_PoleId, set[Handle]]  # carrier pole -> the ports its side poles hid


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Reach:
    """What column reach voting reads (the first six) and leaves for the cell assembly."""

    state: _Poles
    nets: _Nets
    specs: Mapping[Handle, FunctionSpec]
    drawn_of: Mapping[Handle, DrawnFunction]
    in_poles: set[Handle]
    # V1: the ports whose side V1 fixes (`ChainRecords.fixed`)
    fixed: frozenset[Handle] = frozenset()
    # group -> _Group, filled by the voting
    groups: dict[int, _Group] = dataclasses.field(default_factory=dict)
    votes: dict[Handle, dict[int, list[tuple[Handle, bool]]]] = dataclasses.field(
        default_factory=lambda: defaultdict(dict)
    )  # fn -> group -> hits
    # (function, group) -> lane (C9)
    lane_hit: dict[tuple[Handle, int], int] = dataclasses.field(default_factory=dict)
    # (function, group) -> port (C12)
    span_hit: dict[tuple[Handle, int], Handle] = dataclasses.field(default_factory=dict)
    # function -> symbol port (C12)
    span_symbol: dict[Handle, str] = dataclasses.field(default_factory=dict)
    alias: dict[int, int] = dataclasses.field(default_factory=dict)  # a merged group -> its lead
    extra: dict[int, tuple[list[Handle], list[Handle]]] = dataclasses.field(
        default_factory=lambda: defaultdict(lambda: ([], []))
    )  # group -> (above, below)


@dataclasses.dataclass(slots=True, kw_only=True, eq=False)
class _Cells:
    """What the cell assembly reads, and the cells, `placed` and `drawn_in` it fills."""

    poles: dict[_PoleId, _Pole]
    edge_poles: set[_PoleId]
    edge_top: set[_PoleId]
    upper_of: dict[_PoleId, Handle]
    flipped: set[Handle]
    turned: set[Handle]
    sides: dict[_PoleId, list[Handle]]
    side_info: dict[Handle, tuple[bool, bool]]
    carrier_of: dict[Handle, Handle]
    extra: dict[int, tuple[list[Handle], list[Handle]]]
    lane_hit: dict[tuple[Handle, int], int]
    span_symbol: dict[Handle, str]
    specs: Mapping[Handle, FunctionSpec]
    # lower pin -> the upper it faces
    face_of: dict[Handle, Handle] = dataclasses.field(default_factory=dict)
    placed: set[Handle] = dataclasses.field(default_factory=set)
    # function -> the cells that drew it
    drawn_in: dict[Handle, list[Cell]] = dataclasses.field(default_factory=dict)
    cells: list[Cell] = dataclasses.field(default_factory=list)  # the column being built
    index: int = 0
    lane: int = 0
    kept: bool = False  # the current row holds a cell

    def begin_row(self) -> None:
        """A new row: lane 0, no cell kept yet (a method, so no caller narrows `kept` to False)."""
        self.lane, self.kept = 0, False

    def step(self) -> None:
        """A cell stands in the current lane: the next lane, and the row is kept."""
        self.lane += 1
        self.kept = True


@dataclasses.dataclass(slots=True, eq=False)
class _Row:
    """One chain position's row: its functions, side functions and the face rows around it."""

    row: list[Handle | None] = dataclasses.field(default_factory=list)
    side_row: list[Handle] = dataclasses.field(default_factory=list)
    face_row: list[Handle | tuple[str, bool, Handle, Handle]] = dataclasses.field(
        default_factory=list
    )
    face_above: list[tuple[str, bool, Handle, Handle]] = dataclasses.field(default_factory=list)
