"""Validator: green-yellow is protective earth, a PE port sits on a PE net (decision model-0123)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.colours import coloured_conductors
from fransys_model.derive.facts.pe_cores import core_on_pe_not_gnye
from fransys_model.derive.facts.potentials import on_declared_net, on_pe_net, pe_ports_off_pe
from fransys_model.derive.facts.roles import conductor_role, port_role
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import conductors, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor

CORE_ON_PE_NOT_GNYE: Final[str] = "CORE_ON_PE_NOT_GNYE"
GNYE_NOT_PE: Final[str] = "GNYE_NOT_PE"
PE_NOT_GNYE: Final[str] = "PE_NOT_GNYE"
PE_PORT_OFF_PE: Final[str] = "PE_PORT_OFF_PE"
_GNYE: Final[str] = "GNYE"


def _gnye_finding(model: Model, conductor: Conductor, subjects: tuple[Id[Any], ...]) -> Finding:
    """`GNYE_NOT_PE`: an `ERROR` on a declared net, a `WARNING` on a net no declared net lists."""
    if on_declared_net(model, conductor.a):
        text = f"conductor {ref(conductor)} is green-yellow but its net is not PE"
        return finding(GNYE_NOT_PE, Severity.ERROR, subjects, text)
    text = (
        f"conductor {ref(conductor)} is green-yellow (GNYE) but is not on a PE net: recolour it, "
        "or declare the PE net with d.earth"
    )
    return finding(GNYE_NOT_PE, Severity.WARNING, subjects, text)


def _conductor_findings(model: Model) -> list[Finding]:
    found = []
    for conductor_id, colour, facet in coloured_conductors(model):
        conductor = conductors(model)[conductor_id]
        subjects = (conductor.id,) if facet is None else (conductor.id, facet)
        on_pe = on_pe_net(model, conductor.a)
        if colour == _GNYE and not on_pe:
            found.append(_gnye_finding(model, conductor, subjects))
        single = conductor_role(model, conductor.id).wire and conductor.carrier is None
        if single and on_pe and colour not in {"", _GNYE}:
            text = f"wire {ref(conductor)} is on a PE net but coloured {colour!r}, not GNYE"
            found.append(finding(PE_NOT_GNYE, Severity.WARNING, subjects, text))
    return found


def _core_findings(model: Model) -> list[Finding]:
    """`CORE_ON_PE_NOT_GNYE`: a core that is not GNYE with an end on a PE-role port."""
    found = []
    for conductor_id, colour, facet in coloured_conductors(model):
        conductor = conductors(model)[conductor_id]
        roles = (port_role(model, conductor.a), port_role(model, conductor.b))
        if facet is None and core_on_pe_not_gnye(colour, roles):
            text = (
                f"core {ref(conductor)} is {colour} but lands on a PE port: "
                "the PE core is GNYE (IEC 60204-1)"
            )
            found.append(finding(CORE_ON_PE_NOT_GNYE, Severity.ERROR, (conductor.id,), text))
    return found


def check_earth(model: Model) -> tuple[Finding, ...]:
    """The four earth codes over the PE nets `power_kind` reads."""
    port_findings = [
        finding(
            PE_PORT_OFF_PE,
            Severity.WARNING,
            (port,),
            f"port {ref(ports(model)[port])} has role PE but its net is not PE",
        )
        for port in pe_ports_off_pe(model)
    ]
    return ordered(_conductor_findings(model) + _core_findings(model) + port_findings)
