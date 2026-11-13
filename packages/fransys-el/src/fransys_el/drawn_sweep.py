"""The finished-drawing sweep: every finding the drawn netlist and the page geometry give."""

from typing import TYPE_CHECKING

from .drawing_invariants import drawing_invariant_findings
from .drawn_identity_marks import marking_findings
from .drawn_nets import not_drawn_findings
from .drawn_pairs import dangling_findings, loop_findings
from .drawn_power import power_findings
from .drawn_rails import rail_findings
from .drawn_references import reference_findings
from .drawn_shorts import ink_findings, short_findings, wrong_port_findings

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model

    from .drawn_netlist import Netlist

__all__ = ["drawing_sweep"]


def drawing_sweep(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """The findings of the drawn netlist `net`: geometry, shorts, joins, loops and markers."""
    return (
        *drawing_invariant_findings(net),
        *not_drawn_findings(model, net),
        *short_findings(net),
        *ink_findings(net),
        *wrong_port_findings(net),
        *power_findings(net, model),
        *rail_findings(net, model),
        *marking_findings(net, model),
        *loop_findings(net),
        *reference_findings(net),
        *dangling_findings(net),
    )
