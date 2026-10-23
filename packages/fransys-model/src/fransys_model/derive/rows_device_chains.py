"""The row shapes of `device_chains`: its input candidate and its chain output (LC2)."""

from typing import Any

from fransys_model.kernel import AuthoringKey, Id, value
lazy from fransys_model.vocab.core import Function, Item, Port


@value
class ChainCandidate:
    """One function-level record offered to `device_chains`; the caller computes every flag once.

    `connector`: a connector function. `boxed`: no symbol names it. `plain`: no terminal and
    drawn here. `group_path`, `unit` and `location_path` tell its block. `rank`: its designation's
    natural rank. `ports` are in port order.
    """

    function: Id[Function]
    item: Id[Item]
    key: AuthoringKey
    connector: bool
    boxed: bool
    plain: bool
    group_path: tuple[Id[Any], ...]
    in_unit: Id[Any] | None
    location_path: tuple[Id[Any], ...]
    rank: int
    ports: tuple[Id[Port], ...]


@value
class ChainPin:
    """A pin of the fed device and the feeder's pin wired to it."""

    fed: Id[Port]
    feeder: Id[Port]


@value
class ChainHop:
    """The wires from the upper device (`feeder`) to the lower (`fed`), upper pin order."""

    fed: Id[Item]
    feeder: Id[Item]
    pins: tuple[ChainPin, ...]


@value
class ChainRow:
    """Devices of one block wired hop to hop, `members` top to bottom; a ring has `closing`."""

    members: tuple[Id[Item], ...]
    hops: tuple[ChainHop, ...]
    closing: ChainHop | None


@value
class DeviceChains:
    """Every chain in order. `chained`, the items in any chain, keep their connectors whole."""

    chains: tuple[ChainRow, ...]

    @property
    def chained(self) -> frozenset[Id[Item]]:
        """The items in any chain."""
        return frozenset(m for chain in self.chains for m in chain.members)
