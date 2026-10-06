"""T7 (layout-0106, EF-B2): a link-less two-port function on a through path pairs in marking order.

The stage fallback pairs the two ports in declared order; the vocab order (9 before 10) is not
supplied on the read side yet, so this stays a strict xfail until it is (CLEANUP-STEP1 step 5).
"""

import dataclasses

import pytest
from samples import drawn, function_spec, hid

from fransys_layout.stages import PortSpec, Role
from fransys_layout.stages._chain_poles import build_poles


@pytest.mark.xfail(
    strict=True, reason="T7: the link-less pair uses declared order, not marking order"
)
def test_a_link_less_two_port_function_pairs_in_marking_order() -> None:
    """Ports declared `10` then `9`: the pole's first end is `9`."""
    spec = function_spec(1)
    ports = tuple(
        PortSpec(
            port=hid("port", number), name=name, physical_net=hid("net", number), role=Role.CONTROL
        )
        for number, name in ((11, "10"), (12, "9"))
    )
    spec = dataclasses.replace(spec, poles=0, pole_pairs=(), ports=ports)
    state = build_poles((spec,), {spec.function: drawn(1)}, (), (), ())
    assert state.poles[(spec.function, 0)].ports == (hid("port", 12), hid("port", 11))
