"""The finished-drawing sweep: every finding the drawn netlist and the page geometry give."""

from typing import TYPE_CHECKING

from .drawing_invariants import drawing_invariant_findings
from .drawn_nets import not_drawn_findings
from .drawn_pairs import loop_findings, unpaired_findings
from .drawn_shorts import short_findings, wrong_port_findings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Finding, Model

    from .drawn_netlist import Netlist

__all__ = ["drawing_sweep"]


def drawing_sweep(model: Model, net: Netlist, found: Sequence[Finding]) -> tuple[Finding, ...]:
    """The findings of the drawn netlist `net`: geometry, shorts, joins, loops and markers.

    `found` are the findings so far; a port they name NET_CUT_BY_SET is not expected drawn joined.
    """
    cut = {s.value for f in found if f.code == "NET_CUT_BY_SET" for s in f.subjects}
    return (
        *drawing_invariant_findings(net),
        *not_drawn_findings(model, net, cut),
        *short_findings(model, net),
        *wrong_port_findings(model, net),
        *loop_findings(net),
        *unpaired_findings(net),
    )
