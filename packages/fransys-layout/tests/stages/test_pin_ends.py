"""model-0188: a pin cell shares its port with its function; discovery keys the port per end."""

import dataclasses

from samples import connection, drawn, function_spec, hid

from fransys_layout.stages import PortRef
from fransys_layout.stages.chains import ChainRecords
from fransys_layout.stages.pin_ends import pin_keyed


def _records(*, pin: bool) -> ChainRecords:
    """Function 1 and a pin cell 3 of its port 12; a wire inside (to 2) and one outside (to 4)."""
    real, other = function_spec(1), function_spec(2)
    cell = dataclasses.replace(
        function_spec(3),
        ports=(dataclasses.replace(real.ports[1], name="in"),),
        pin_function=real.function if pin else None,
    )
    inside = connection(1, 1, 2)
    outside = dataclasses.replace(
        connection(2, 4, 3), a=PortRef(function=cell.function, port=real.ports[1].port)
    )
    return ChainRecords(
        (real, other, cell),
        (drawn(1), drawn(2), dataclasses.replace(drawn(3), ports=drawn(1).ports[1:])),
        (inside, outside),
        (),
        (),
    )


def test_a_pin_cell_sharing_a_port_gets_its_own_key_at_every_use() -> None:
    before = _records(pin=True)
    after = pin_keyed(before)
    shared = hid("port", 12)
    key = next(p.port for s in after.functions if s.function == hid("function", 3) for p in s.ports)
    assert key != shared
    assert [p.port for s in after.functions for p in s.ports].count(shared) == 1
    assert {end.port for c in after.connections for end in (c.a, c.b)} >= {key, shared}
    assert next(d for d in after.drawn if d.function == hid("function", 3)).ports[0].port == key


def test_records_without_a_shared_pin_port_come_back_unchanged() -> None:
    plain = _records(pin=False)
    assert pin_keyed(plain) is plain
