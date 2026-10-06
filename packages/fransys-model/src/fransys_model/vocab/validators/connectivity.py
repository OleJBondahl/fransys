"""Validator: declared nets vs the physical closure (design/connectivity.md, ROADMAP WP12)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.closure import net_of, physical_nets
from fransys_model.vocab.membership import enclosing_boards
from fransys_model.vocab.potentials import physical_potentials
from fransys_model.vocab.tables import (
    conductors,
    functions,
    items,
    mates,
    nets,
    ports,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Net
    from fransys_model.vocab.core import Function, Item, Port

NET_UNREALISED: Final[str] = "NET_UNREALISED"
NET_SHORTED: Final[str] = "NET_SHORTED"
PORT_UNCONNECTED: Final[str] = "PORT_UNCONNECTED"
CONDUCTOR_ON_UNINSTALLED: Final[str] = "CONDUCTOR_ON_UNINSTALLED"
NET_POTENTIAL_CONFLICT: Final[str] = "NET_POTENTIAL_CONFLICT"


def _finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=tuple(subjects), message=message)


def _label(net: Net) -> str:
    """What a person calls a net: its name if it has one, else its authoring key."""
    return net.name if net.name is not None else key_text(net)


class _Plant:
    """The lookups the checks share, built once per model."""

    def __init__(self, model: Model) -> None:
        self.model = model
        self.nets = nets(model)
        self.ports = ports(model)
        self.conductors = conductors(model)
        self.items = items(model)
        self.functions = functions(model)
        self.closure = physical_nets(model)
        self.declared: dict[Id[Port], list[Id[Net]]] = {}
        for net in self.nets.values():
            for port in net.ports:
                self.declared.setdefault(port, []).append(net.id)
        names: dict[Id[Function], set[str]] = {}
        for port in self.ports.values():
            names.setdefault(port.function, set()).add(port.name)
        # a port is on a mate when the partner function has a port of the same name
        self.mated = {
            (end, name)
            for mate in mates(model).values()
            for end, partner in ((mate.a, mate.b), (mate.b, mate.a))
            for name in names.get(end, set()) & names.get(partner, set())
        }
        self._boards_of: dict[Id[Item], frozenset[Id[Item]]] = {}

    def item_of(self, port: Id[Port]) -> Item:
        return self.items[self.functions[self.ports[port].function].item]

    def boards_of(self, item: Item) -> frozenset[Id[Item]]:
        """The board items among `item` and its ancestors (`enclosing_boards`, model-0040)."""
        if item.id not in self._boards_of:
            self._boards_of[item.id] = frozenset(enclosing_boards(self.model, item.id))
        return self._boards_of[item.id]

    def board_realised(self, net: Net) -> bool:
        """Whether one board item is an ancestor-or-self of every port's item."""
        common: frozenset[Id[Item]] | None = None
        for port in net.ports:
            boards = self.boards_of(self.item_of(port))
            common = boards if common is None else common & boards
        return bool(common)


def _unrealised(plant: _Plant) -> list[Finding]:
    found = []
    for net in plant.nets.values():
        pieces = {net_of(plant.model, port) for port in net.ports}
        if len(pieces) > 1 and not plant.board_realised(net):
            message = f"net {_label(net)} falls into {len(pieces)} physical nets"
            found.append(_finding(NET_UNREALISED, Severity.WARNING, (net.id,), message))
    return found


def _per_physical_net(plant: _Plant) -> list[Finding]:
    found = []
    for physical in plant.closure:
        declared = {net for port in physical.ports for net in plant.declared.get(port, ())}
        if len(declared) <= 1:
            continue
        names = ", ".join(sorted(_label(plant.nets[net]) for net in declared))
        message = f"one physical net joins the declared nets {names}"
        found.append(_finding(NET_SHORTED, Severity.ERROR, declared, message))
        by_potential = physical_potentials(plant.model, physical)
        if len(by_potential) > 1:
            message = f"one physical net joins the rails {', '.join(sorted(by_potential))}"
            rails = (net for ids in by_potential.values() for net in ids)
            found.append(_finding(NET_POTENTIAL_CONFLICT, Severity.ERROR, rails, message))
    return found


def _conductor_findings(plant: _Plant) -> list[Finding]:
    found = []
    for conductor in plant.conductors.values():
        pulled = {
            item.id: item
            for item in (plant.item_of(conductor.a), plant.item_of(conductor.b))
            if not item.installed
        }
        if pulled:
            names = ", ".join(sorted(key_text(item) for item in pulled.values()))
            message = (
                f"conductor {key_text(conductor)} lands on an item that is not installed: {names}"
            )
            found.append(
                _finding(
                    CONDUCTOR_ON_UNINSTALLED, Severity.WARNING, (conductor.id, *pulled), message
                )
            )
    return found


def _unconnected(plant: _Plant) -> list[Finding]:
    wired = {end for conductor in plant.conductors.values() for end in (conductor.a, conductor.b)}
    return [
        _finding(
            PORT_UNCONNECTED,
            Severity.INFO,
            (port.id,),
            f"port {key_text(port)} is in no net and on no conductor or mate",
        )
        for port in plant.ports.values()
        if port.id not in plant.declared
        and port.id not in wired
        and (port.function, port.name) not in plant.mated
    ]


def check_connectivity(model: Model) -> tuple[Finding, ...]:
    """Compare every declared `Net` against the physical closure; connectivity.md lists findings.

    Findings come back sorted by `(code, subjects, message)`.
    """
    plant = _Plant(model)
    found = [
        *_unrealised(plant),
        *_per_physical_net(plant),
        *_conductor_findings(plant),
        *_unconnected(plant),
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
