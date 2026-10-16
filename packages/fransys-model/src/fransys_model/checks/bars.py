"""Validator: a bar's ports are all PE, the only conductor bar modelled (spec PE-BAR, B5)."""

from typing import Final

from fransys_model.derive.facts.bars import is_bar_port
from fransys_model.derive.facts.roles import is_pe_port
from fransys_model.kernel import Finding, Model, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import ports

BAR_NOT_PE: Final[str] = "BAR_NOT_PE"


def check_bars(model: Model) -> tuple[Finding, ...]:
    """`BAR_NOT_PE`: one finding for each port of a `bar` function whose role is not `pe`."""
    found = [
        Finding(
            code=BAR_NOT_PE,
            severity=Severity.ERROR,
            subjects=(port.id,),
            message=(
                f"bar port {ref(port)} is not PE: a bar carries protective earth only until "
                "'copper bar drawing (owner question)' is ruled; set role = \"pe\" in the part file"
            ),
        )
        for port in ports(model).values()
        if not is_pe_port(model, port.id) and is_bar_port(model, port.id)
    ]
    return tuple(sorted(found, key=lambda f: (f.subjects, f.message)))
