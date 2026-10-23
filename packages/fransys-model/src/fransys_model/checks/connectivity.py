"""Validator: declared nets vs the physical closure (design/connectivity.md)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.closure import net_of, net_on_one_board, physical_nets, port_item
from fransys_model.derive.facts.net_crossings import net_crossings
from fransys_model.derive.facts.net_facts import declared_nets_of, is_earth_net
from fransys_model.derive.facts.potentials import physical_potentials
from fransys_model.derive.facts.wired_ports import half_connected
from fransys_model.kernel import Finding, Severity, natural_join
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import conductors, items, nets

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Net

NET_UNREALISED: Final[str] = "NET_UNREALISED"
NET_SHORTED: Final[str] = "NET_SHORTED"
FUNCTION_HALF_CONNECTED: Final[str] = "FUNCTION_HALF_CONNECTED"
CONDUCTOR_ON_UNINSTALLED: Final[str] = "CONDUCTOR_ON_UNINSTALLED"
NET_POTENTIAL_CONFLICT: Final[str] = "NET_POTENTIAL_CONFLICT"


def _label(net: Net) -> str:
    """What a person calls a net: its name if it has one, else its reference."""
    return net.name if net.name is not None else ref(net)


def _unrealised(model: Model) -> list[Finding]:
    found = []
    for net in nets(model).values():
        if is_earth_net(model, net.id) or net.id in net_crossings(model):
            continue
        pieces = {net_of(model, port) for port in net.ports}
        if len(pieces) > 1 and not net_on_one_board(model, net.ports):
            message = f"net {_label(net)} falls into {len(pieces)} physical nets"
            found.append(finding(NET_UNREALISED, Severity.WARNING, (net.id,), message))
    return found


def _one_intent(model: Model, declared: set[Id[Net]]) -> bool:
    """Whether every declared net is named, and all share one name (model-0156)."""
    names = {nets(model)[net].name for net in declared}
    return len(names) == 1 and None not in names


def _shorting_nets(model: Model, declared: set[Id[Net]]) -> set[Id[Net]]:
    """The declared nets that count for a short: a crossing net drops its unnamed neighbours.

    A net across a unit boundary has its own finding (layout-0322), which replaces only the
    cascade it causes; two differently named nets that meet are a short, boundary or not.
    """
    if not net_crossings(model).keys() & declared:
        return declared
    return {net for net in declared if nets(model)[net].name is not None}


def _per_physical_net(model: Model) -> list[Finding]:
    found = []
    for physical in physical_nets(model):
        declared = {net for port in physical.ports for net in declared_nets_of(model, port)}
        if len(declared) <= 1:
            continue
        shorting = _shorting_nets(model, declared)
        if len(shorting) > 1 and not _one_intent(model, shorting):
            names = natural_join(_label(nets(model)[net]) for net in shorting)
            message = f"one physical net joins the declared nets {names}"
            found.append(finding(NET_SHORTED, Severity.ERROR, shorting, message))
        by_potential = physical_potentials(model, physical)
        if len(by_potential) > 1:
            message = f"one physical net joins the rails {natural_join(by_potential)}"
            rails = (net for ids in by_potential.values() for net in ids)
            found.append(finding(NET_POTENTIAL_CONFLICT, Severity.ERROR, rails, message))
    return found


def _conductor_findings(model: Model) -> list[Finding]:
    found = []
    for conductor in conductors(model).values():
        pulled = {
            item.id: item
            for item in (items(model)[port_item(model, end)] for end in (conductor.a, conductor.b))
            if not item.installed
        }
        if pulled:
            names = natural_join(ref(item) for item in pulled.values())
            message = f"conductor {ref(conductor)} lands on an item that is not installed: {names}"
            subjects = (conductor.id, *pulled)
            found.append(finding(CONDUCTOR_ON_UNINSTALLED, Severity.WARNING, subjects, message))
    return found


def _half_connected(model: Model) -> list[Finding]:
    return [
        finding(
            FUNCTION_HALF_CONNECTED,
            Severity.WARNING,
            (opened.id,),
            f"{ref(function)} is connected at one port and open at {ref(opened)}",
        )
        for function, opened in half_connected(model)
    ]


def check_connectivity(model: Model) -> tuple[Finding, ...]:
    """Compare every declared `Net` against the physical closure; connectivity.md lists findings.

    Findings come back sorted by `(code, subjects, message)`.
    """
    return ordered(
        [
            *_unrealised(model),
            *_per_physical_net(model),
            *_conductor_findings(model),
            *_half_connected(model),
        ]
    )
