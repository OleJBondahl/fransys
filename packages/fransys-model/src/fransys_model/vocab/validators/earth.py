"""Validator: green-yellow is protective earth, a PE port sits on a PE net (decision model-0123)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.closure import net_of
from fransys_model.vocab.enums import ConductorKind, PortRole
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.potentials import on_pe_net
from fransys_model.vocab.tables import conductors, facets_of, items, nets, ports

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Port

GNYE_NOT_PE: Final[str] = "GNYE_NOT_PE"
PE_NOT_GNYE: Final[str] = "PE_NOT_GNYE"
PE_PORT_OFF_PE: Final[str] = "PE_PORT_OFF_PE"
_GNYE: Final[str] = "GNYE"


def _on_declared_net(model: Model, declared: frozenset[Id[Port]], port: Id[Port]) -> bool:
    physical = net_of(model, port)
    return physical is not None and physical.ports[0] in declared


def _core_colours(model: Model) -> dict[Id[Conductor], str]:
    """The colour of each core: its carrier's product `core_colours[index - 1]`."""
    by_part = {facet.subject: facet for facet in facets_of(model, CableProductFacet).values()}
    found: dict[Id[Conductor], str] = {}
    for core in facets_of(model, CoreFacet).values():
        carrier = conductors(model)[core.subject].carrier
        part = None if carrier is None else items(model)[carrier].part
        product = by_part.get(part) if part is not None else None
        if product is not None and 1 <= core.index <= len(product.core_colours):
            found[core.subject] = product.core_colours[core.index - 1]
    return found


def _coloured(model: Model) -> Iterator[tuple[Conductor, str, Id[Any] | None]]:
    """Each conductor with its colour and the wire facet it came from (`None` for a core)."""
    for facet in facets_of(model, WireFacet).values():
        yield conductors(model)[facet.subject], facet.colour, facet.id
    for conductor_id, colour in _core_colours(model).items():
        yield conductors(model)[conductor_id], colour, None


def _finding(code: str, severity: Severity, subjects: tuple[Id[Any], ...], text: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=subjects, message=text)


def _gnye_finding(
    conductor: Conductor, subjects: tuple[Id[Any], ...], *, declared: bool
) -> Finding:
    """`GNYE_NOT_PE`: an `ERROR` on a declared net, a `WARNING` on a net no declared net lists."""
    if declared:
        text = f"conductor {ref(conductor)} is green-yellow but its net is not PE"
        return _finding(GNYE_NOT_PE, Severity.ERROR, subjects, text)
    text = (
        f"conductor {ref(conductor)} is green-yellow (GNYE) but is not on a PE net: recolour it, "
        "or declare the PE net with d.earth"
    )
    return _finding(GNYE_NOT_PE, Severity.WARNING, subjects, text)


def _conductor_findings(model: Model) -> list[Finding]:
    found = []
    declared = _declared_nets(model)
    for conductor, colour, facet in _coloured(model):
        subjects = (conductor.id,) if facet is None else (conductor.id, facet)
        on_pe = on_pe_net(model, conductor.a)
        if colour == _GNYE and not on_pe:
            found.append(
                _gnye_finding(
                    conductor, subjects, declared=_on_declared_net(model, declared, conductor.a)
                )
            )
        single = conductor.kind is ConductorKind.WIRE and conductor.carrier is None
        if single and on_pe and colour not in {"", _GNYE}:
            text = f"wire {ref(conductor)} is on a PE net but coloured {colour!r}, not GNYE"
            found.append(_finding(PE_NOT_GNYE, Severity.WARNING, subjects, text))
    return found


def _declared_nets(model: Model) -> frozenset[Id[Port]]:
    """First port of each physical net that holds a port of any declared net."""
    physical = (net_of(model, port) for net in nets(model).values() for port in net.ports)
    return frozenset(net.ports[0] for net in physical if net is not None)


def _is_wired(model: Model, port: Id[Port]) -> bool:
    """Whether `port` shares a physical net with another port: a lone port has nothing to flag."""
    physical = net_of(model, port)
    return physical is not None and len(physical.ports) > 1


def _port_findings(model: Model) -> list[Finding]:
    return [
        _finding(
            PE_PORT_OFF_PE,
            Severity.WARNING,
            (port.id,),
            f"port {ref(port)} has role PE but its net is not PE",
        )
        for port in ports(model).values()
        if port.role is PortRole.PE and _is_wired(model, port.id) and not on_pe_net(model, port.id)
    ]


def check_earth(model: Model) -> tuple[Finding, ...]:
    """`GNYE_NOT_PE`, `PE_NOT_GNYE` and `PE_PORT_OFF_PE` over the PE nets `power_kind` reads."""
    found = _conductor_findings(model) + _port_findings(model)
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
