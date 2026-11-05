"""Field case: two identical I/O boards tagged U1 and U2 at one place, joined by a cable between their connectors.
The bug: a stub's far end was sliced out of the port text, so it read the unit's root tag for both boards.
Fixed by model-0134, the one rendering in fransys_model.derive gives the far end its instance tag, not a string slice."""

from typing import Any

import fransys as fr
from test_black_box_prints_no_instance_tag import _board

from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import functions, ports


def _port(model: fr.Model, device: fr.Device, name: str) -> Any:
    return next(i for i, p in ports(model).items() if functions(model)[p.function].item == device.id and p.name == name)


def test_each_far_end_carries_its_instance_tag() -> None:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    a = d.add(_board, "U1")
    b = d.add(_board, "U2")
    cable = d.cable("W1", "DEMO-CBL-4G1.5")
    cable.core(1, a.J1["1"], b.J1["1"])
    model = fr.build(d).model
    head_a, tail_a = stub_far_end(model, _port(model, a.J1, "1"))
    head_b, tail_b = stub_far_end(model, _port(model, b.J1, "1"))
    assert head_a.endswith("-U1-J1")
    assert head_b.endswith("-U2-J1")
    assert (tail_a, tail_b) == (":1", ":1")
