"""EL2 rail nature: the net-class and potential sites keep their output when they read net facts.

One digest over the cabinet model: each port's potential rank and current, power kind, power
text, rail-terminal flag, the stands, each net's power kind and text, and the baseline listing.
"""

from hashlib import sha256

from cabinet import build_cabinet

from fransys_model.derive import (
    is_rail_terminal,
    port_potential_current,
    port_potential_rank,
    port_power_kind,
    port_power_text,
    power_kind,
    power_text,
)
from fransys_model.derive.baseline_listing import _net_rows
from fransys_model.derive.baseline_rules import ListingRules
from fransys_model.derive.stands import stands
from fransys_model.kernel import freeze
from fransys_model.vocab.tables import items, nets, ports

_DIGEST = "1e7af1d76049f5140b7ac505780db25b23d01a1398514a55e4f757e51eb55564"


def observed() -> str:
    """The text every switched site prints on the cabinet model, sorted by id."""
    model = freeze(build_cabinet(cpu=True))
    lines = [
        repr(
            (
                p,
                port_potential_rank(model, p),
                port_potential_current(model, p),
                port_power_kind(model, p),
                port_power_text(model, p),
            )
        )
        for p in sorted(ports(model))
    ]
    lines += [repr((n, power_kind(model, n), power_text(model, n))) for n in sorted(nets(model))]
    lines += [repr((i, is_rail_terminal(model, i))) for i in sorted(items(model))]
    lines.append(repr(sorted(stands(model).items())))
    lines.append(repr(_net_rows(model, None, ListingRules())))
    return "\n".join(lines)


def test_the_sites_print_what_they_printed_before_the_switch() -> None:
    """The digest was taken before any site read a net fact (re-taken: R1289 and earlier)."""
    assert sha256(observed().encode()).hexdigest() == _DIGEST
