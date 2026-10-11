"""Chain discovery's port keys: a pin cell's port is its own key, per connection end (model-0188).

A unit's boundary function and the pin cell the parent draws for it share one model port. A
conductor inside the unit ends on the function and one outside ends on the pin cell
(`land_on_pins` names the function at each end), so discovery keys each such port by its end.
"""

import dataclasses
from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.kernel import Id

if TYPE_CHECKING:
    from .chains import ChainRecords
    from .types import DrawnFunction, FunctionSpec, Handle, PortRef

_PIN_PORT = "pin-port"

type _Shared = frozenset[tuple[Handle, Handle]]


def pin_keyed(records: ChainRecords) -> ChainRecords:
    """`records` with each pin cell's port renamed where another function also owns that port."""
    owners = Counter(p.port for spec in records.functions for p in spec.ports)
    shared = frozenset(
        (spec.function, p.port)
        for spec in records.functions
        if spec.pin_function is not None
        for p in spec.ports
        if owners[p.port] > 1
    )
    if not shared:
        return records
    return dataclasses.replace(
        records,
        functions=tuple(_spec(s, shared) for s in records.functions),
        drawn=tuple(_drawn(d, shared) for d in records.drawn),
        connections=tuple(
            dataclasses.replace(c, a=_end(c.a, shared), b=_end(c.b, shared))
            for c in records.connections
        ),
        net_groups=tuple(
            dataclasses.replace(g, ports=tuple(_end(ref, shared) for ref in g.ports))
            for g in records.net_groups
        ),
    )


def _key(function: Handle, port: Handle, shared: _Shared) -> Handle:
    return Id(kind=_PIN_PORT, value=port.value) if (function, port) in shared else port


def _end(ref: PortRef, shared: _Shared) -> PortRef:
    return dataclasses.replace(ref, port=_key(ref.function, ref.port, shared))


def _spec(spec: FunctionSpec, shared: _Shared) -> FunctionSpec:
    ports = (dataclasses.replace(p, port=_key(spec.function, p.port, shared)) for p in spec.ports)
    return dataclasses.replace(spec, ports=tuple(ports))


def _drawn(drawn: DrawnFunction, shared: _Shared) -> DrawnFunction:
    ports = (dataclasses.replace(p, port=_key(drawn.function, p.port, shared)) for p in drawn.ports)
    return dataclasses.replace(drawn, ports=tuple(sorted(ports, key=lambda p: p.port)))
