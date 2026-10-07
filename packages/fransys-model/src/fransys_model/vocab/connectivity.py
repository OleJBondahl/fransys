"""Vocabulary: connectivity kinds (design/vocabulary.md 6 "Connectivity", 8)."""

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record

from .core import Function, Item, Port
from .enums import ConductorKind, NetClass
from .templates import _holder, _order_ends


@record(kind="net")
class Net:
    """Declared intent: a set of ports that are one potential or one signal.

    Example: a 24V supply net names the PSU `+` port and every load's supply port.
    N-ary; `ports` is a set, stored sorted by id. `potential` names the rail this net
    is (`"L1"`, `"24V"`, `"0V"`, `"PE"`); `None` is an ordinary net. It is a fact about
    the plant, read by wire-colour rules and ladder discovery.

    Guarded by `validators.connectivity` (`NET_UNREALISED`, `NET_SHORTED`,
    `NET_POTENTIAL_CONFLICT`).
    """

    id: Id[Net]
    key: AuthoringKey
    name: str | None
    net_class: NetClass
    ports: tuple[Id[Port], ...]
    potential: str | None = None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store `ports` in id order; a port listed twice is refused.

        Anything that is not a tuple of `Id`s is left as it is: `freeze()` reports it.
        """
        ports = self.ports
        if type(ports) is not tuple or not all(type(port) is Id for port in ports):
            return
        ordered = tuple(sorted(ports))
        if len(set(ordered)) != len(ordered):
            msg = "a net lists a port twice"
            raise SchemaError(msg, kind="net", record_id=_holder(self))
        object.__setattr__(self, "ports", ordered)


@record(kind="conductor")
class Conductor:
    """Realisation: an exactly-two-ended physical connection.

    Example: one core of the invented cable `W012` example is
    a `Conductor(kind=CORE, carrier=<the cable item>)` between a transmitter's port and
    a terminal's `EXTERNAL` port. `a`/`b` are stored in id order; direction is not a
    fact.

    Net membership lives only in `Net.ports`: a conductor carries
    no net of its own. Guarded by `validators.connectivity` and `validators.cables`.
    """

    id: Id[Conductor]
    key: AuthoringKey
    a: Id[Port]
    b: Id[Port]
    kind: ConductorKind
    carrier: Id[Item] | None
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store the ends in id order; the same port at both ends is refused."""
        _order_ends(self, "conductor", "a conductor joins two different ports")


@record(kind="mate")
class Mate:
    """Two CONNECTOR or TERMINAL functions plugged together; equal-named ports become conductive.

    Example: a harness housing's connector `Function` mates with a board-edge
    connector `Function` (design/examples.md 11); net closure runs through the mate
    into the board net. `a`/`b` are stored in id order; direction is not a fact. Read by
    `derive.closure`.
    """

    id: Id[Mate]
    key: AuthoringKey
    a: Id[Function]
    b: Id[Function]
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Store the ends in id order; the same function at both ends is refused."""
        _order_ends(self, "mate", "a mate joins two different functions")
