"""F6: a changeover's chained throw is picked by its throw role binding, not by its port name.

`build_poles` pairs the through path's ports and records the throw on, and the throw off, that
pole. The ports here are named `x1`..`x3`, so no name says which throw is which.

Can-fail probe: `_changeover_pairs` choosing `chained` by `p.name in on` (the through ends' names)
fails the second test, whose drawing binds the make port away from the symbol port `no`.
"""

import dataclasses

from samples import drawn, function_spec, hid, through_geometry

from fransys_layout.geometry import ThroughPath
from fransys_layout.stages import PortSpec, Role
from fransys_layout.stages._chain_poles import build_poles
from fransys_layout.stages.types import DrawnPort, KindRoles

_THROWS = (("x1", "common"), ("x2", "break"), ("x3", "make"))


def _built(bound: dict[str, str]):
    """A changeover of ports `x1`..`x3`, drawn through com to no, each port bound by `bound`."""
    spec = function_spec(1)
    ports = tuple(
        PortSpec(
            port=hid("port", 11 + i),
            name=name,
            physical_net=hid("net", i),
            role=Role.CONTROL,
            throw=throw,
        )
        for i, (name, throw) in enumerate(_THROWS)
    )
    spec = dataclasses.replace(
        spec,
        poles=0,
        pole_pairs=(),
        ports=ports,
        roles=KindRoles(contact=True, contact_changeover=True),
    )
    geometry = dataclasses.replace(through_geometry(), through=ThroughPath(start="com", end="no"))
    d = dataclasses.replace(
        drawn(1),
        geometry=geometry,
        ports=tuple(DrawnPort(port=p.port, symbol_port=bound[p.name]) for p in ports),
    )
    return build_poles((spec,), {spec.function: d}, (), (), ()), ports


def test_the_chained_throw_is_the_one_the_role_binds_to_the_through_path() -> None:
    """Make binds to `no`, the through path's end: it is chained and break is off."""
    state, ports = _built({"x1": "com", "x2": "nc", "x3": "no"})
    assert state.throw_pairs == [(ports[2].port, ports[1].port)]


def test_the_role_decides_not_the_name_drawn_at_the_through_ends() -> None:
    """Break is drawn at `no` (the name comparison would chain it), yet make is still chained."""
    state, ports = _built({"x1": "com", "x2": "no", "x3": "nc"})
    assert state.throw_pairs == [(ports[2].port, ports[1].port)]
