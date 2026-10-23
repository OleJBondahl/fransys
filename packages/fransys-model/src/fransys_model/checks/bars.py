"""Validator: a bar's ports are all PE, the only conductor bar modelled (spec PE-BAR, B5)."""

from typing import Final

from fransys_model.checks._finding import finding
from fransys_model.derive.facts.bars import bar_ports_not_pe
from fransys_model.kernel import Finding, Model, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import ports

BAR_NOT_PE: Final[str] = "BAR_NOT_PE"


def check_bars(model: Model) -> tuple[Finding, ...]:
    """`BAR_NOT_PE`: one finding for each port of a `bar` function whose role is not `pe`."""
    found = [
        finding(
            BAR_NOT_PE,
            Severity.ERROR,
            (port,),
            f"bar port {ref(ports(model)[port])} is not PE: a bar carries protective earth only "
            "until 'copper bar drawing (owner question)' is ruled; set role = \"pe\" in the part "
            "file",
        )
        for port in bar_ports_not_pe(model)
    ]
    return tuple(sorted(found, key=lambda f: (f.subjects, f.message)))
